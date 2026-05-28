package nero.router

import chisel3._
import chisel3.util._
import chisel3.probe.{Probe, ProbeValue, define, read}
import chisel3.layer._

import nero.parameters.NeroParameters
import nero.bundle._
import nero.util._

private[router] object Directions extends Enumeration {
  type Direction = Value
  val North, East, West, South, Local0, Local1, Local2, Local3 = Value
}

class Router(param: NeroParameters) extends Module {
  // Cardinal direction ports
  val northInbound = IO(Flipped(new AXISBundle(param)))
  val northOutbound = IO((new AXISBundle(param)))
  val eastInbound = IO(Flipped(new AXISBundle(param)))
  val eastOutbound = IO((new AXISBundle(param)))
  val westInbound = IO(Flipped(new AXISBundle(param)))
  val westOutbound = IO((new AXISBundle(param)))
  val southInbound = IO(Flipped(new AXISBundle(param)))
  val southOutbound = IO((new AXISBundle(param)))

  // Local direction ports
  val local0Inbound = IO(Flipped(new AXISBundle(param)))
  val local0Outbound = IO((new AXISBundle(param)))
  val local1Inbound = IO(Flipped(new AXISBundle(param)))
  val local1Outbound = IO((new AXISBundle(param)))
  val local2Inbound = IO(Flipped(new AXISBundle(param)))
  val local2Outbound = IO((new AXISBundle(param)))
  val local3Inbound = IO(Flipped(new AXISBundle(param)))
  val local3Outbound = IO((new AXISBundle(param)))

  // Decoders
  private val northDecoder = Module(new DecoderWrapper(param))
  private val eastDecoder = Module(new DecoderWrapper(param))
  private val westDecoder = Module(new DecoderWrapper(param))
  private val southDecoder = Module(new DecoderWrapper(param))
  private val local0Decoder = Module(new DecoderWrapper(param))
  private val local1Decoder = Module(new DecoderWrapper(param))
  private val local2Decoder = Module(new DecoderWrapper(param))
  private val local3Decoder = Module(new DecoderWrapper(param))

  // Arbiters
  private val northArbiter = Module(new ArbiterWrapper(param))
  private val eastArbiter = Module(new ArbiterWrapper(param))
  private val westArbiter = Module(new ArbiterWrapper(param))
  private val southArbiter = Module(new ArbiterWrapper(param))
  private val local0Arbiter = Module(new ArbiterWrapper(param))
  private val local1Arbiter = Module(new ArbiterWrapper(param))
  private val local2Arbiter = Module(new ArbiterWrapper(param))
  private val local3Arbiter = Module(new ArbiterWrapper(param))

  private val payloads = Wire(Vec(8, new NeroPayload(param)))
  payloads(0) := northInbound.payload.bits
  payloads(1) := eastInbound.payload.bits
  payloads(2) := westInbound.payload.bits
  payloads(3) := southInbound.payload.bits
  payloads(4) := local0Inbound.payload.bits
  payloads(5) := local1Inbound.payload.bits
  payloads(6) := local2Inbound.payload.bits
  payloads(7) := local3Inbound.payload.bits

  private def connect(
      inboundDecoder: DecoderWrapper,
      outboundArbiter: ArbiterWrapper,
      inboundWire: AXISBundle,
      outboundWire: AXISBundle,
      direction: Directions.Direction
  ) = {
    val dirId = direction.id
    val decoderValids = Reverse(
      Cat(
        northDecoder.decoderValid(dirId),
        eastDecoder.decoderValid(dirId),
        westDecoder.decoderValid(dirId),
        southDecoder.decoderValid(dirId),
        local0Decoder.decoderValid(dirId),
        local1Decoder.decoderValid(dirId),
        local2Decoder.decoderValid(dirId),
        local3Decoder.decoderValid(dirId)
      )
    )
    val slaveReadys = Reverse(
      Cat(
        northArbiter.slaveReadys(dirId),
        eastArbiter.slaveReadys(dirId),
        westArbiter.slaveReadys(dirId),
        southArbiter.slaveReadys(dirId),
        local0Arbiter.slaveReadys(dirId),
        local1Arbiter.slaveReadys(dirId),
        local2Arbiter.slaveReadys(dirId),
        local3Arbiter.slaveReadys(dirId)
      )
    )

    inboundDecoder.masterInbound :<>= inboundWire
    inboundDecoder.slaveReadys := slaveReadys

    outboundWire :<>= outboundArbiter.slaveInbound
    outboundArbiter.masterPayloads := payloads
    outboundArbiter.decoderValid := decoderValids
  }

  // Wiring
  connect(
    northDecoder,
    northArbiter,
    northInbound,
    northOutbound,
    Directions.North
  )
  connect(eastDecoder, eastArbiter, eastInbound, eastOutbound, Directions.East)
  connect(westDecoder, westArbiter, westInbound, westOutbound, Directions.West)
  connect(
    southDecoder,
    southArbiter,
    southInbound,
    southOutbound,
    Directions.South
  )
  connect(
    local0Decoder,
    local0Arbiter,
    local0Inbound,
    local0Outbound,
    Directions.Local0
  )
  connect(
    local1Decoder,
    local1Arbiter,
    local1Inbound,
    local1Outbound,
    Directions.Local1
  )
  connect(
    local2Decoder,
    local2Arbiter,
    local2Inbound,
    local2Outbound,
    Directions.Local2
  )
  connect(
    local3Decoder,
    local3Arbiter,
    local3Inbound,
    local3Outbound,
    Directions.Local3
  )

  // Debugging probes
  val northDecoderValid = IO(Probe(UInt(8.W), VerbosePrint))
  val eastDecoderValid = IO(Probe(UInt(8.W), VerbosePrint))
  val westDecoderValid = IO(Probe(UInt(8.W), VerbosePrint))
  val southDecoderValid = IO(Probe(UInt(8.W), VerbosePrint))
  val local0DecoderValid = IO(Probe(UInt(8.W), VerbosePrint))
  val local1DecoderValid = IO(Probe(UInt(8.W), VerbosePrint))
  val local2DecoderValid = IO(Probe(UInt(8.W), VerbosePrint))
  val local3DecoderValid = IO(Probe(UInt(8.W), VerbosePrint))

  val northArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))
  val eastArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))
  val westArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))
  val southArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))
  val local0ArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))
  val local1ArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))
  val local2ArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))
  val local3ArbiterReady = IO(Probe(UInt(8.W), VerbosePrint))

  val northArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))
  val eastArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))
  val westArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))
  val southArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))
  val local0ArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))
  val local1ArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))
  val local2ArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))
  val local3ArbiterGrants = IO(Probe(UInt(8.W), VerbosePrint))

  block(VerbosePrint) {
    val northDecoderValidProbe = ProbeValue(northDecoder.decoderValid)
    val eastDecoderValidProbe = ProbeValue(eastDecoder.decoderValid)
    val westDecoderValidProbe = ProbeValue(westDecoder.decoderValid)
    val southDecoderValidProbe = ProbeValue(southDecoder.decoderValid)
    val local0DecoderValidProbe = ProbeValue(local0Decoder.decoderValid)
    val local1DecoderValidProbe = ProbeValue(local1Decoder.decoderValid)
    val local2DecoderValidProbe = ProbeValue(local2Decoder.decoderValid)
    val local3DecoderValidProbe = ProbeValue(local3Decoder.decoderValid)

    define(northDecoderValid, northDecoderValidProbe)
    define(eastDecoderValid, eastDecoderValidProbe)
    define(westDecoderValid, westDecoderValidProbe)
    define(southDecoderValid, southDecoderValidProbe)
    define(local0DecoderValid, local0DecoderValidProbe)
    define(local1DecoderValid, local1DecoderValidProbe)
    define(local2DecoderValid, local2DecoderValidProbe)
    define(local3DecoderValid, local3DecoderValidProbe)

    val northArbiterReadyProbe = ProbeValue(northArbiter.slaveReadys)
    val eastArbiterReadyProbe = ProbeValue(eastArbiter.slaveReadys)
    val westArbiterReadyProbe = ProbeValue(westArbiter.slaveReadys)
    val southArbiterReadyProbe = ProbeValue(southArbiter.slaveReadys)
    val local0ArbiterReadyProbe = ProbeValue(local0Arbiter.slaveReadys)
    val local1ArbiterReadyProbe = ProbeValue(local1Arbiter.slaveReadys)
    val local2ArbiterReadyProbe = ProbeValue(local2Arbiter.slaveReadys)
    val local3ArbiterReadyProbe = ProbeValue(local3Arbiter.slaveReadys)

    define(northArbiterReady, northArbiterReadyProbe)
    define(eastArbiterReady, eastArbiterReadyProbe)
    define(westArbiterReady, westArbiterReadyProbe)
    define(southArbiterReady, southArbiterReadyProbe)
    define(local0ArbiterReady, local0ArbiterReadyProbe)
    define(local1ArbiterReady, local1ArbiterReadyProbe)
    define(local2ArbiterReady, local2ArbiterReadyProbe)
    define(local3ArbiterReady, local3ArbiterReadyProbe)

    define(northArbiterGrants, northArbiter.grants)
    define(eastArbiterGrants, eastArbiter.grants)
    define(westArbiterGrants, westArbiter.grants)
    define(southArbiterGrants, southArbiter.grants)
    define(local0ArbiterGrants, local0Arbiter.grants)
    define(local1ArbiterGrants, local1Arbiter.grants)
    define(local2ArbiterGrants, local2Arbiter.grants)
    define(local3ArbiterGrants, local3Arbiter.grants)
  }
}

// Defined private, as these act as a 'glue'.
private[router] class DecoderWrapper(
    param: NeroParameters
) extends Module {
  val masterInbound = IO(Flipped(new AXISBundle(param)))
  val decoderValid = IO(Output(UInt(8.W)))
  val slaveReadys = IO(Input(UInt(8.W)))

  private val routeFilter = Module(new RoutingFilter(param))
  routeFilter.src := masterInbound.payload.bits.src
  routeFilter.dest := masterInbound.payload.bits.dest
  routeFilter.local := masterInbound.payload.bits.local

  private val availableRoute = Reverse(
    Cat(
      routeFilter.available.north,
      routeFilter.available.east,
      routeFilter.available.west,
      routeFilter.available.south,
      routeFilter.available.local0,
      routeFilter.available.local1,
      routeFilter.available.local2,
      routeFilter.available.local3
    )
  )
  private val availableArbiters =
    Fill(8, masterInbound.payload.valid) & availableRoute
  decoderValid := PriorityEncoderOH(availableArbiters)

  masterInbound.payload.ready := (decoderValid & slaveReadys).orR
}

private[router] class ArbiterWrapper(param: NeroParameters) extends Module {
  val slaveInbound = IO(new AXISBundle(param))
  val slaveReadys = IO(Output(UInt(8.W)))
  val decoderValid = IO(Input(UInt(8.W)))
  val masterPayloads = IO(Input(Vec(8, new NeroPayload(param))))
  val grants = IO(Output(Probe(UInt(8.W), VerbosePrint)))

  private val roundRobin = Module(
    new RoundRobinArbiter(4 + param.localTilesPerRouter)
  )
  private val hasGrant = roundRobin.io.grant.orR
  private val hasValid = decoderValid.orR

  slaveReadys := Fill(8, slaveInbound.payload.ready) & roundRobin.io.grant
  roundRobin.io.req := decoderValid
  roundRobin.io.ack := slaveInbound.payload.ready & hasValid

  slaveInbound.payload.valid := hasGrant
  slaveInbound.payload.bits := Mux1H(
    roundRobin.io.grant.asBools.zip(masterPayloads).map {
      case (grant: Bool, payload: NeroPayload) => grant -> payload
    }
  )

  block(VerbosePrint) {
    val grantValue = ProbeValue(roundRobin.io.grant)
    define(grants, grantValue)
  }
}
