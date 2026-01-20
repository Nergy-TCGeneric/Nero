package nero.router

import nero.bundle._
import nero.util._
import chisel3._
import chisel3.util._

class Demux1to8[T <: Data](gen: T) extends Module {
  val io = IO(new Bundle {
    val in = Input(gen)
    val sel = Input(UInt(3.W))
    val out = Output(Vec(8, gen))
  })

  io.out.foreach(_ := 0.U.asTypeOf(gen))
  io.out(io.sel) := io.in
}

class RouteFilter(
    x: Int,
    y: Int,
    tileCount: Int
) extends Module {
  val io = IO(new Bundle {
    val TDEST = Flipped(UInt((2 * log2Ceil(tileCount + 1)).W))
    val north = Bool()
    val west = Bool()
    val south = Bool()
    val east = Bool()
    val localX0 = Bool()
    val localX1 = Bool()
    val localY0 = Bool()
    val localY1 = Bool()
  })

  val destX = io.TDEST(log2Ceil(tileCount + 1) - 1, 0)
  val destY = io.TDEST(2 * log2Ceil(tileCount + 1) - 1, log2Ceil(tileCount + 1))
  val diffX = (destX - x.U).asSInt
  val diffY = (destY - y.U).asSInt

  val rangeBound = log2Ceil(5).S

  when(diffY < 0.S) {
    io.south := true.B
    io.north := false.B
    io.localY0 := false.B
    io.localY1 := false.B
  }.elsewhen(diffY > rangeBound) {
    io.south := false.B
    io.north := true.B
    io.localY0 := false.B
    io.localY1 := false.B
  }.otherwise {
    io.south := false.B
    io.north := false.B
    io.localY0 := diffY === 0.S
    io.localY1 := diffY =/= 0.S
  }

  when(diffX < 0.S) {
    io.west := true.B
    io.east := false.B
    io.localX0 := false.B
    io.localX1 := false.B
  }.elsewhen(diffY > rangeBound) {
    io.west := false.B
    io.east := true.B
    io.localX0 := false.B
    io.localX1 := false.B
  }.otherwise {
    io.west := false.B
    io.east := false.B
    io.localX0 := diffX === 0.S
    io.localX1 := diffX =/= 0.S
  }
}

class InboundPort(
    x: Int,
    y: Int,
    tileCount: Int,
    timestampWidth: Int
) extends Module {
  require(timestampWidth >= 0, "Timestamp width must be non-negative!")

  // val input = IO(Flipped(new AXISBundle(tileCount, timestampWidth)))
  val input = IO(
    Flipped(Irrevocable(new AXISPayload(tileCount, timestampWidth)))
  )

  // Toward ports in cardinal direction
  val cardinalOutputs =
    Seq.fill(4)(IO(Irrevocable(new AXISPayload(tileCount, timestampWidth))))

  // Toward ports in local port
  val localOutputs =
    Seq.fill(4)(IO(Irrevocable(new AXISPayload(tileCount, timestampWidth))))

  // Internals
  private val BUFFER_DEPTH = 4
  val packetBuffer = Module(
    new Queue(new AXISPayload(tileCount, timestampWidth), BUFFER_DEPTH)
  )

  input.ready := !packetBuffer.io.enq.ready
  packetBuffer.io.enq.valid := input.valid
  packetBuffer.io.enq.bits := input.bits

  private val readySignals =
    cardinalOutputs.map(_.ready) ++ localOutputs.map(_.ready)
  // val readyWire = Cat(readySignals)

  val routeFilter = Module(new nero.router.RouteFilter(x, y, tileCount))
  routeFilter.io.TDEST := input.bits.TDEST
  val readyWire = Cat(
    readySignals(0) & routeFilter.io.north,
    readySignals(1) & routeFilter.io.west,
    readySignals(2) & routeFilter.io.east,
    readySignals(3) & routeFilter.io.south,
    readySignals(4) & routeFilter.io.localX0 & routeFilter.io.localY0,
    readySignals(5) & routeFilter.io.localX1 & routeFilter.io.localY0,
    readySignals(6) & routeFilter.io.localX0 & routeFilter.io.localY1,
    readySignals(7) & routeFilter.io.localX1 & routeFilter.io.localY1
  )

  val encoder = Module(new nero.util.PriorityEncoder(8))
  encoder.io.input := readyWire
  packetBuffer.io.deq.ready := encoder.io.valid

  val dataDemux = Module(
    new Demux1to8(new AXISPayload(tileCount, timestampWidth))
  )
  dataDemux.io.in := packetBuffer.io.deq.bits
  dataDemux.io.sel := encoder.io.index

  private val dataOutputs =
    cardinalOutputs.map(_.bits) ++ localOutputs.map(_.bits)
  dataOutputs.zip(dataDemux.io.out).foreach {
    case (dataOut, demux) => {
      dataOut := demux
    }
  }

  val validDemux = Module(new Demux1to8(Bool()))
  validDemux.io.in := packetBuffer.io.deq.valid
  validDemux.io.sel := encoder.io.index

  private val validOutputs =
    cardinalOutputs.map(_.valid) ++ localOutputs.map(_.valid)
  validOutputs.zip(validDemux.io.out).foreach {
    case (validOut, demux) => { validOut := demux }
  }
}
