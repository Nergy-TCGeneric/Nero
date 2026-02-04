package nero.router

import org.scalatest.funspec.AnyFunSpec

import circt.stage.ChiselStage
import nero.parameters.NeroParameters

class RouterSpec extends AnyFunSpec {
  val stubParam = NeroParameters(4, 0, 4)
  describe("AXI-S Router") {
    it("should generate verilog") {
      ChiselStage.emitSystemVerilog(new Router(stubParam))
    }
  }
}
