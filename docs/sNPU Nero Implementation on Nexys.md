---
created: 2025-10-20 19:10
modified: 2025-10-20 19:10
---
# Revision Log

| date     | version | change logs   |
| -------- | ------- | ------------- |
| 25-10-20 | v1      | Initial draft |

# Architecture

Refer [[sNPU Architecture v0.2 (Single-Die Specification)]] for more details.

# Requirement

- Able to ship on Artix-7 100T Nexys board. (Single FPGA chip with peripherals)
- Place as much internal tiles as possible, at least 4×4.
- Run at least 100MHz clock, from single clock source.

# Objective

- Make a FPGA-proven implementation of [[sNPU Architecture v0.2 (Single-Die Specification)]].
	- A nice way to say: *make it work first.*
	- Aims `Nero-P` architecture.

# Logical Placement

**Legend**
- □ : Blank outer tiles
- E : Egress node (inner -> outer aggregation)
- I : Ingress node (outer -> inner)
- ■ : Inner tiles

```
□□IE□□
□■■■■□
□■■■■□
□■■■■□
□■■■■□
□□□□□□
```

Rationale behind it:
- 4×4 is pretty small, no need to sweat about the hop delay (at most 7 clocks).
- Until injection, neurons stay idle.

# Protocol

Internal tiles use AXI-Stream(AXIS). For outer tiles, anything compatible with UART is fine, but I'll just stick to AXIS to simplify the implementation.

# Outer tile implementation

## Speed considerations

Nexys board has only UART connection with host, @ ~1MHz (if supersampling exists). That's *pretty* slow for spike injection, even for modest mesh size like 4 by 4. So instead of relying on UART directly, we need a buffer so it can keep up the speed.

## Outer tile flow

(Inner tiles) <-> AXIS Data Memory <-> AXIS ~ UART Converter <-> UART module <-> (Host)

### AXIS Data Memory

This data memory is for retaining certain data that have to be reused over and over. Unlike the FIFO, it's literally just a small memory, prehaps 18k BRAM, with 'count' register. Accumulate the spike packet from host or internal tiles and read them sequentially later.

# Design parameter decision

| Name                    | Value | Note                                  |
| ----------------------- | ----- | ------------------------------------- |
| `NEURON_TILE_COUNT`     | 4     |                                       |
| `WEIGHT_WIDTH`          | 16    | Q4.12, Fixed point                    |
| `DOPAMINE_BUFFER_WIDTH` | 0     | DA-STDP is out-of-scope for now       |
| `E_TRACE_WIDTH`         | 8     | Just in case when 4-bit is not enough |
| `R_PERIOD_WIDTH`        | 0     | No refractory period                  |
| `TIMESTAMP_WIDTH`       | 32    |                                       |
| `MAX_CONNECTION`        | 16    | For implementing dense connection     |

# Neuron implementation

Exposes `TREADY`, `TVALID` and `TLAST`(tied to `1'b1`) to in/outbound ports.
Rest of implementation is quite straightforward.

## Packet

Uses AXIS(AXI-Stream) Interface.

| Name    | Bit length | Note                                             |
| ------- | ---------- | ------------------------------------------------ |
| TCLK    | 1          | Mandatory AXIS signal                            |
| TRESETn | 1          | Mandatory AXIS signal                            |
| TVALID  | 1          | Mandatory AXIS signal                            |
| TREADY  | 1          | For backpressure implementation                  |
| TID     | 4          | TID = {`src_x`, `src_y`}                         |
| TDEST   | 4          | TDEST = {`dest_x`, `dest_y`}                     |
| TDATA   | 34         | TDEST = {`src_type`, `packet_type`, `timestamp`} |
|         |            |                                                  |

## Implementing ordinary differential equations (ODEs)

Since this implementation uses fixed point which is an integer, when it comes to modeling decay, bit-shifting it by constant amount (= by decay constant) and subtracting it would be enough for each clock with some cost of precision.

When received a spike from somewhere, however, adding or subtracting $w$ to $V_{mem}$ must take a priority over decay. That is, if multiple spike comes in consecutively, decay would *not* happen until such spike train stops.

### Canonical Signed Digit(CSD) for multiplying constant

A discrete decay equation, where $I(t) = 0$,
$$V[t+1] = V[t] e^{\frac{-1}{\tau}}$$
We know that $e^{\frac{-1}{\tau}}$ is a constant, where $\tau$ is a decay constant. However even for integers, mutliplication is non-trivial. Fortunately when multiplicand is constant, we can use CSD here to optimize the hardware to greater degree.

For example, multiplying A with 478 can be decomposed into:
$$ A \times 478 = A \times (256 + 128 + 64 + 16 + 8 + 4 + 2)$$
However, as we're using Q4.12, we need 12 adders in total and that's equivalent to 4-depth. Instead of only using addition, we can use CSD to optimize it further:
$$A \times 478 = A \times (512 - 32 - 2)$$
Now it only requires **two** adder. Subtraction is trivial as we can use 2's complement here. But this powerful optimization comes with a cost: $\tau$ must be a *synthesis-time constant*. However as reconfigurability is out-of-scope for now, that's not a big issue.

# Router implementation

Deploy 4-depth AXIS FIFO for each cardinal inbound ports. Assert `TREADY` if FIFO is not full, Deassert if otherwise. Neurons can only accept one spike at a time, so no buffer is required at the local port.

# Error handling

Can't read if an error has occured from each tile for now, because spec does not define how to read diagnostics(even a flag register) from internal tiles. I have no choice but rely on spike output.

I'll just use `$fatal` for this case, though it's a simulation-time construct not a synthesizable one. And I'll just manually see if something went wrong from simulation when something doesn't work as expected on FPGA.

Maybe building an 'emulator' would help detecting any discrepancies can happen. No need to be high-performance right now, just a prototype will do.

# Verification considerations

## Neuron

- Does the $V_{mem}$ gets updated correctly if spiked?
- Does the $V_{mem}$ gets decayed if no input is present but $V_{mem}$ is non-zero over time?
- Does it generate outbound packet when $V_{mem} > V_t$?
	- Does $V_{mem}$ becomes 0 after firing a spike? (since this has no refractory period)
## Router

- Do routers *eventually* deliver spike to destination at bounded time?
	- At best, it should take at most 8 clocks ( = 2 + 6 ).
- **No spike is ever dropped?**