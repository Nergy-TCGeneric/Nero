package nero

import circt.stage.ChiselStage
import nero.router._
import nero.neuron.Neuron

object Main extends App {
  println("Neuron")
  println("CHIRRTL: ")
  println(ChiselStage.emitCHIRRTL(new Neuron(0, 0, true, 4, 4)))

  println("SystemVerilog: ")
  println(ChiselStage.emitSystemVerilog(new Neuron(0, 0, true, 4, 4)))

  println("Inbound Port")
  println("CHIRRTL: ")
  println(ChiselStage.emitCHIRRTL(new InboundPort(0, 0, 4, 4)))

  println("SystemVerilog: ")
  println(ChiselStage.emitSystemVerilog(new InboundPort(0, 0, 4, 4)))
}
