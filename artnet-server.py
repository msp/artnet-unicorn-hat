# Art-Net protocol for Pimoroni Unicorn Hat
# Open Pixel Control protocol for Pimoroni Unicorn Hat
# License: MIT
import unicornhathd as unicorn
from twisted.internet import protocol, endpoints
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor

# Adjust the LED brightness as needed.
unicorn.brightness(0.5)

class ArtNet(DatagramProtocol):

    def datagramReceived(self, data, (host, port)):
        if ((len(data) > 18) and (data[0:8] == "Art-Net\x00")):
            rawbytes = map(ord, data)
            opcode = rawbytes[8] + (rawbytes[9] << 8)
            protocolVersion = (rawbytes[10] << 8) + rawbytes[11]
            if ((opcode == 0x5000) and (protocolVersion >= 14)):
                sequence = rawbytes[12]
                physical = rawbytes[13]
                sub_net = (rawbytes[14] & 0xF0) >> 4
                universe = rawbytes[14] & 0x0F
                net = rawbytes[15]
                rgb_length = (rawbytes[16] << 8) + rawbytes[17]
                #print "seq %d phy %d sub_net %d uni %d net %d len %d" % \
                #(sequence, physical, sub_net, universe, net, rgb_length)
                idx = 18
                x = 0
                y = 0
                while ((idx < (rgb_length+18)) and (y < 8)):
                    r = rawbytes[idx]
                    idx += 1
                    g = rawbytes[idx]
                    idx += 1
                    b = rawbytes[idx]
                    idx += 1
                    unicorn.set_pixel(x, y, r, g, b)
                    x += 1
                    if (x > 7):
                        x = 0
                        y += 1
                unicorn.show()

class OPC(protocol.Protocol):
    # Parse Open Pixel Control protocol. See http://openpixelcontrol.org/.
    MAX_LEDS = 256
    WIDTH = 16
    parseState = 0
    pktChannel = 0
    pktCommand = 0
    pktLength = 0
    pixelCount = 0
    pixelLimit = 0

    def dataReceived(self, data):
        rawbytes = map(ord, data)
        #print "len(rawbytes) %d" % len(rawbytes)
        #print rawbytes
        i = 0
        while (i < len(rawbytes)):
            #print "parseState %d i %d" % (OPC.parseState, i)
            if (OPC.parseState == 0):   # get OPC.pktChannel
                OPC.pktChannel = rawbytes[i]
                i += 1
                OPC.parseState += 1
            elif (OPC.parseState == 1): # get OPC.pktCommand
                OPC.pktCommand = rawbytes[i]
                i += 1
                OPC.parseState += 1
            elif (OPC.parseState == 2): # get OPC.pktLength.highbyte
                OPC.pktLength = rawbytes[i] << 8
                i += 1
                OPC.parseState += 1
            elif (OPC.parseState == 3): # get OPC.pktLength.lowbyte
                OPC.pktLength |= rawbytes[i]
                i += 1
                OPC.parseState += 1
                OPC.pixelCount = 0
                OPC.pixelLimit = min(3*OPC.MAX_LEDS, OPC.pktLength)
                print "OPC.pktChannel %d OPC.pktCommand %d OPC.pktLength %d OPC.pixelLimit %d" % \
                    (OPC.pktChannel, OPC.pktCommand, OPC.pktLength, OPC.pixelLimit)
                if (OPC.pktLength > 3*OPC.MAX_LEDS):
                    print "Received pixel packet exeeds size of buffer! Data discarded."
                if (OPC.pixelLimit == 0):
                    OPC.parseState = 0
            elif (OPC.parseState == 4):
                copyBytes = min(OPC.pixelLimit - OPC.pixelCount, len(rawbytes) - i)
                if (copyBytes > 0):
                    OPC.pixelCount += copyBytes
                    print "OPC.pixelLimit %d OPC.pixelCount %d copyBytes %d" % \
                            (OPC.pixelLimit, OPC.pixelCount, copyBytes)
                    if ((OPC.pktCommand == 0) and (OPC.pktChannel <= 1)):
                        x = 0
                        y = 0
                        iLimit = i + copyBytes
                        while ((i < iLimit) and (y < OPC.WIDTH)):
                            #print "i %d" % (i)
                            r = rawbytes[i]
                            i += 1
                            g = rawbytes[i]
                            i += 1
                            b = rawbytes[i]
                            i += 1
                            unicorn.set_pixel(x, y, r, g, b)
                            #print "x %d y %d r %d g %d b %d" % (x,y,r,g,b)
                            x += 1
                            if (x > (OPC.WIDTH - 1)):
                                x = 0
                                y += 1

                        if (OPC.pixelCount >= OPC.pixelLimit):
                            unicorn.show()
                    else:
                        i += copyBytes
                    if (OPC.pixelCount == OPC.pktLength):
                        OPC.parseState = 0
                    else:
                        OPC.parseState += 1
            elif (OPC.parseState == 5):
                discardBytes = min(OPC.pktLength - OPC.pixelLimit, len(rawbytes) - i)
                #print "discardBytes %d" % (discardBytes)
                OPC.pixelCount += discardBytes
                i += discardBytes
                if (OPC.pixelCount >= OPC.pktLength):
                    print "Reseting parse state.."
                    OPC.parseState = 0
                if (discardBytes == 0):
                    OPC.parseState = 0
                    print("Unexpected 0 bytes to discard")
            else:
                print "Invalid OPC.parseState %d" % (OPC.parseState)


class OPCFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return OPC()

reactor.listenUDP(6454, ArtNet())
endpoints.serverFromString(reactor, "tcp:7890").listen(OPCFactory())
reactor.run()
