package nero

import chisel3._
import chisel3.util

import nero.router._
import nero.neuron._

class Cluster(
    x: Int,
    y: Int,
    tileCount: Int,
    timestampWidth: Int
) extends Module {
  require(timestampWidth >= 0, "Timestamp width must be non-negative.")

  private val requiredSize = util.log2Ceil(4)
  private val neurons = for {
    nX <- x to x + requiredSize
    nY <- y to y + requiredSize
  } yield (Module(new Neuron(nX, nY, false, tileCount, timestampWidth)))

  // Ports
  // Connection order:
  // North, West, East, South, (0, 0), (1, 0), (0, 1), (1, 1)
  val northInboundPort = Module(
    new InboundPort(x, y, tileCount, timestampWidth)
  )
  val northOutboundPort = Module(
    new OutboundPort(tileCount, timestampWidth)
  )

  val westInboundPort = Module(
    new InboundPort(x, y, tileCount, timestampWidth)
  )
  val westOutboundPort = Module(
    new OutboundPort(tileCount, timestampWidth)
  )

  val southInboundPort = Module(
    new InboundPort(x, y, tileCount, timestampWidth)
  )
  val southOutboundPort = Module(
    new OutboundPort(tileCount, timestampWidth)
  )

  val eastInboundPort = Module(
    new InboundPort(x, y, tileCount, timestampWidth)
  )
  val eastOutboundPort = Module(
    new OutboundPort(tileCount, timestampWidth)
  )

  northOutboundPort.cardinalPorts(0) := northInboundPort.cardinalOutputs(0)
  northOutboundPort.cardinalPorts(1) := westInboundPort.cardinalOutputs(0)
  northOutboundPort.cardinalPorts(2) := eastInboundPort.cardinalOutputs(0)
  northOutboundPort.cardinalPorts(3) := southInboundPort.cardinalOutputs(0)
  northOutboundPort.cardinalPorts(4) := neurons(0).output
  northOutboundPort.cardinalPorts(5) := neurons(1).output
  northOutboundPort.cardinalPorts(6) := neurons(2).output
  northOutboundPort.cardinalPorts(7) := neurons(3).output

  westOutboundPort.cardinalPorts(0) := northInboundPort.cardinalOutputs(1)
  westOutboundPort.cardinalPorts(1) := westInboundPort.cardinalOutputs(1)
  westOutboundPort.cardinalPorts(2) := eastInboundPort.cardinalOutputs(1)
  westOutboundPort.cardinalPorts(3) := southInboundPort.cardinalOutputs(1)
  westOutboundPort.cardinalPorts(4) := neurons(0).output
  westOutboundPort.cardinalPorts(5) := neurons(1).output
  westOutboundPort.cardinalPorts(6) := neurons(2).output
  westOutboundPort.cardinalPorts(7) := neurons(3).output

  eastOutboundPort.cardinalPorts(0) := northInboundPort.cardinalOutputs(2)
  eastOutboundPort.cardinalPorts(1) := westInboundPort.cardinalOutputs(2)
  eastOutboundPort.cardinalPorts(2) := eastInboundPort.cardinalOutputs(2)
  eastOutboundPort.cardinalPorts(3) := southInboundPort.cardinalOutputs(2)
  eastOutboundPort.cardinalPorts(4) := neurons(0).output
  eastOutboundPort.cardinalPorts(5) := neurons(1).output
  eastOutboundPort.cardinalPorts(6) := neurons(2).output
  eastOutboundPort.cardinalPorts(7) := neurons(3).output

  southOutboundPort.cardinalPorts(0) := northInboundPort.cardinalOutputs(3)
  southOutboundPort.cardinalPorts(1) := westInboundPort.cardinalOutputs(3)
  southOutboundPort.cardinalPorts(2) := eastInboundPort.cardinalOutputs(3)
  southOutboundPort.cardinalPorts(3) := southInboundPort.cardinalOutputs(3)
  southOutboundPort.cardinalPorts(4) := neurons(0).output
  southOutboundPort.cardinalPorts(5) := neurons(1).output
  southOutboundPort.cardinalPorts(6) := neurons(2).output
  southOutboundPort.cardinalPorts(7) := neurons(3).output
}
