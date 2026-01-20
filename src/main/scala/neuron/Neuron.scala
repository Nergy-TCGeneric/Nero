package nero.neuron

import chisel3._
import chisel3.util._

import nero.bundle._

object NeuronState extends ChiselEnum {
  val decay, spike, fire = Value
}

// Complies Nero-P specification.
class Neuron(
    x: Int,
    y: Int,
    isExhibitory: Boolean,
    tileCount: Int,
    timestampWidth: Int
) extends Module {
  // Neuron-specific constants.
  // TODO: Should be propagated from the top module instead.
  private val ENTRIES = 8
  private val DATA_WIDTH = 16.W

  // TODO: Should extend these ports into 8, including cardinal link and neurons, even autpases.
  val input = IO(
    Flipped(Irrevocable(new AXISPayload(tileCount, timestampWidth)))
  )
  val output = IO(Irrevocable(new AXISPayload(tileCount, timestampWidth)))

  // Q4.12
  private val memPotential = RegInit(0.S(DATA_WIDTH))
  private val threshold = RegInit(0.S(DATA_WIDTH))
  private val weights = SyncReadMem(ENTRIES, SInt(DATA_WIDTH))

  // Takes 1 cycle delay, which FSM already accounts for.
  // Use {src_x, src_y} as an address of weight.
  private val weight = weights.read(input.bits.TSRC, input.valid)

  // Neuron FSM control
  private val state = RegInit(NeuronState.decay)

  // Spike launcher
  private val launcher = Module(
    new SpikeLauncher(x, y, isExhibitory, tileCount, timestampWidth)
  )

  private val shouldFireSpike = memPotential >= threshold && launcher.ready
  input.ready := launcher.ready
  output :<>= launcher.output
  launcher.increment := state === NeuronState.fire

  when(state === NeuronState.decay) {
    when(input.valid) {
      state := NeuronState.spike
    }.otherwise {
      state := NeuronState.decay
    }
  }.elsewhen(state === NeuronState.spike) {
    when(shouldFireSpike) {
      state := NeuronState.fire
    }.elsewhen(!input.valid) {
      state := NeuronState.decay
    }.otherwise {
      state := NeuronState.spike
    }
  }.otherwise {
    state := NeuronState.decay
  }

  // Membrane potential update
  when(state === NeuronState.spike) {
    memPotential := memPotential + weight
  }.otherwise {
    // TODO: Use Canonical Signed Digit(CSD) multipler to emulate the decay.
    // This just assumes \tau = 100, which is equivalent to 0.99 (= e^(-1/\tau)).
    memPotential := memPotential
    -(memPotential >> 7)
    -(memPotential >> 9)
    -(memPotential >> 12)
  }
}
