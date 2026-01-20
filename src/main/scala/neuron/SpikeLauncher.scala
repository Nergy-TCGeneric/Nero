package nero.neuron

import chisel3._
import chisel3.util._

import nero.bundle.AXISPayload

class SpikeLauncher(
    x: Int,
    y: Int,
    isExhibitory: Boolean,
    tileCount: Int,
    timestampWidth: Int
) extends Module {

  require(tileCount > 0, "There must be at least one tile.")

  // TODO: Use parameter later
  private val MAX_REQUEST_COUNT = 4
  private val MAX_ENTRIES = 16
  private val ENTRIES = 4

  private val tileCountWidth = log2Ceil(tileCount)

  val output = IO(Irrevocable(new AXISPayload(tileCount, timestampWidth)))
  val increment = IO(Input(Bool()))
  val ready = IO(Output(Bool()))

  private val requestCounter = RegInit(0.U(log2Ceil(MAX_REQUEST_COUNT + 1).W))
  private val addressCounter = RegInit(0.U(log2Ceil(MAX_ENTRIES + 1).W))
  private val timestamp = RegInit(0.U(timestampWidth.W))
  private val destMemory =
    SyncReadMem(MAX_ENTRIES + 1, UInt((2 * tileCountWidth).W))

  private val needDecrement = addressCounter === (MAX_ENTRIES - 1).U
  private val canAcceptRequest = requestCounter < MAX_REQUEST_COUNT.U
  private val isRunning = requestCounter =/= 0.U

  ready := canAcceptRequest

  when(increment && canAcceptRequest) {
    requestCounter := requestCounter + 1.U
  }.elsewhen(needDecrement) {
    requestCounter := requestCounter - 1.U
  }

  when(!isRunning) {
    addressCounter := ENTRIES.U
  }.otherwise {
    when(addressCounter === 0.U) {
      addressCounter := ENTRIES.U
    }.otherwise {
      addressCounter := addressCounter - 1.U
    }
  }

  when(output.valid && output.ready) {
    timestamp := 0.U(timestampWidth.W)
  }.otherwise {
    timestamp := timestamp + 1.U
  }

  output.valid := isRunning
  output.bits.TSRC := Cat(y.U(tileCountWidth.W), x.U(tileCountWidth.W))
  output.bits.TDEST := destMemory.read(addressCounter, isRunning)
  output.bits.TDATA := Cat(timestamp, 0.U(4.W), 0.U(1.W), isExhibitory.B)
}
