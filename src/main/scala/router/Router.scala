package nero.router

import chisel3._
import chisel3.util._

import nero.parameters.NeroParameters
import nero.bundle._

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
    direction: Directions.Direction) = {
      val dirId = direction.id
      val decoderValids = Cat(
        northDecoder.decoderValid(dirId), eastDecoder.decoderValid(dirId), westDecoder.decoderValid(dirId), southDecoder.decoderValid(dirId),
        local0Decoder.decoderValid(dirId), local1Decoder.decoderValid(dirId), local2Decoder.decoderValid(dirId), local3Decoder.decoderValid(dirId)
      )
      val arbiterGrants = Cat(
        northArbiter.grants(dirId), eastArbiter.grants(dirId), westArbiter.grants(dirId), southArbiter.grants(dirId),
        local0Arbiter.grants(dirId), local1Arbiter.grants(dirId), local2Arbiter.grants(dirId), local3Arbiter.grants(dirId)
      )

      inboundDecoder.masterInbound :<>= inboundWire
      inboundDecoder.arbiterGrants := arbiterGrants

      outboundWire :<>= outboundArbiter.slaveInbound
      outboundArbiter.masterPayloads := payloads
      outboundArbiter.decoderValid := decoderValids
  }

  // Wiring
  connect(northDecoder, northArbiter, northInbound, northOutbound, Directions.North)
  connect(eastDecoder, eastArbiter, eastInbound, eastOutbound, Directions.East)
  connect(westDecoder, westArbiter, westInbound, westOutbound, Directions.West)
  connect(southDecoder, southArbiter, southInbound, southOutbound, Directions.South)
  connect(local0Decoder, local0Arbiter, local0Inbound, local0Outbound, Directions.Local0)
  connect(local1Decoder, local1Arbiter, local1Inbound, local1Outbound, Directions.Local1)
  connect(local2Decoder, local2Arbiter, local2Inbound, local2Outbound, Directions.Local2)
  connect(local3Decoder, local3Arbiter, local3Inbound, local3Outbound, Directions.Local3)
}

// Defined private, as these act as a 'glue'.
private[router] class DecoderWrapper(param: NeroParameters) extends Module {
  val masterInbound = IO(Flipped(new AXISBundle(param)))
  val decoderValid = IO(Output(UInt(8.W)))
  val arbiterGrants = IO(Input(UInt(8.W)))

  private val routeFilter = Module(new RoutingFilter(param))
  routeFilter.src := masterInbound.payload.bits.src
  routeFilter.dest := masterInbound.payload.bits.dest
  routeFilter.local := masterInbound.payload.bits.local

  private val availableRoute = Cat(
    routeFilter.available.north, routeFilter.available.east, routeFilter.available.west, routeFilter.available.south,
    routeFilter.available.local0, routeFilter.available.local1, routeFilter.available.local2, routeFilter.available.local3
  )
  private val availableArbiters = Fill(8, masterInbound.payload.valid) & availableRoute
  private val encoded = PriorityEncoderOH(availableRoute)
  decoderValid := availableArbiters & encoded & arbiterGrants

  masterInbound.payload.ready := decoderValid.orR
}

private[router] class ArbiterWrapper(param: NeroParameters) extends Module {
  val slaveInbound = IO(new AXISBundle(param))
  val grants = IO(Output(UInt(8.W)))
  val decoderValid = IO(Input(UInt(8.W)))
  val masterPayloads = IO(Input(Vec(8, new NeroPayload(param))))

  private val roundRobin = Module(new RoundRobinArbiter(4 + param.localTilesPerRouter))
  private val grantBuffer = RegInit(0.U(8.W))
  private val hasGrant = roundRobin.io.grant.orR

  roundRobin.io.req := decoderValid
  roundRobin.io.ack := hasGrant & slaveInbound.payload.ready

  // Placed a buffer in between to disconnect combinatorial cycle here.
  // Slave-side TVALID will be asserted one cycle later.
  grantBuffer := roundRobin.io.grant
  grants := grantBuffer

  slaveInbound.payload.valid := hasGrant
  slaveInbound.payload.bits := Mux1H(
    roundRobin.io.grant.asBools.zip(masterPayloads).map {
      case (grant: Bool, payload: NeroPayload) => grant -> payload
    }
  )
}
