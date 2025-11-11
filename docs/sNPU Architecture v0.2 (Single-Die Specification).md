---
created: 2025-10-19 18:50
modified: 2025-11-10 12:56
---
Previous work:
- [[SNN NoC Fabric]]
- [[Spikeability Checker]]

Related:
- [[sNPU Architecture Roadmap]]

Last updated: 25-11-10 12:56

# Revision Log

| Date       | Version | Change Log                                |
| ---------- | ------- | ----------------------------------------- |
| 2025-10-20 | v0      | Initial Draft                             |
| 2025-10-22 | v0.1    | Specialized to 'Single-Die Specification' |
| 2025-10-25 | v0.2    | Modularized neuron tile composition       |
|            |         |                                           |

# 1. Executive Summary

> [[sNPU Nero|sNPU "Nero"]] is a scalable, modular and tile-based [[Spiking Neural Network (SNN)]] accelerator.

A single die hosts N by N inner tiles arranged in 2D mesh, surrounded by a small number of outer tiles that provide off-chip interface (UART, SPI, PCIe, etc.).
All intra-die communication uses a [[Network-on-Chip (NoC)]] that routes packets via routers to neuron tiles.

The design intentionally keeps many parameters (e.g., neuron counts, weight widths) parameterized so that the same spec drives both FPGA and ASIC implementations.

# 2. Glossary

| Term              | Definition                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Outer tile        | Tile that exposes the off-chip interface. Mainly communicates with host, but optionally with other sNPU chips.                  |
| Inner tile        | Tiles that cannot be accessed from outside directly. Refers a group consists of router and its one or more neuron tiles.        |
| Router (Synapse)  | Core of an inner tile. Implements a spike-routing table and forwards spike to cardinal neighbors or to associated neuron tiles. |
| Neuron tile       | Implements a single spiking neuron based on [[Leaky Integrate and Fire\|LIF]] with learning and neuromodulation support.        |
| Grid coordinate   | 2D integer pair `(x, y)` identifying a tile's position in the mesh.                                                             |
| Packet            | A payload sent over the NoC.                                                                                                    |
| Eligibility trace | A register that records the timing of pre/post-spike events for STDP updates.                                                   |
| Dopamine buffer   | Per-neuron register that decays over time and gates DA-STDP learning.                                                           |

# 3. High-Level Architecture

**Functional Diagram**

```
           +------------+  Host IF +-------------+
           | Outer tile |<-------->|    Host     |
           +--+---------+          +-------------+
              |       ^                           
Inner tile's  |       |                           
protocol      |       |                           
              |       |                           
              v       |                           
           +----------+-+          +-------------+
           | Inner tile |<--....-->| Inner tiles |
           +------------+          +-------------+
                       NoC Connection             
                         (2-D Mesh)               
```

- The mesh is N by N. Each inner tile is linked to its four cardinal neighbors (N, S, E, W).
- Outer tiles are fixed in number (typically 1 or 4) and occupy the periphery. They are the *only* tiles that have an off-chip interface.
- All spike packets travel in *unidirectional bursts* with a simple read/valid handshake along the cardinal links. A router can generate back-pressure to upstream tiles.

**Placement**

```
+-----------------------------------+                              
|     +----------------------+      |                              
|     |     Outer tiles      |      |                              
|     +----------------------+      |                              
| +-+ +---++---++---+     +---+ +-+ |                              
| | | |   ||   ||   |     |   | | | |                              
| | | |   ||   ||   | ... |   | | | |                              
| | | |   ||   ||   |     |   | | | |                              
| | | +---++---++---+     +---+ | | |                              
| |O| +---++---++---+     +---+ |O| |                              
| |u| |   ||   ||   |     |   | |u| |                              
| |t| |   ||   ||   | ... |   | |t| |  UART/SPI/PCIe...  +--------+
| |e| |   ||   ||   |     |   | |e| | via Host interface |        |
| |r| +---++---++---+     +---+ |r| |                    |        |
| | | +---++---++---+     +---+ | | | <----------------> |  Host  |
| |t| |   ||   ||   |     |   | |t| |                    |        |
| |i| |   ||   ||   | ... |   | |i| |                    |        |
| |l| |   ||   ||   |     |   | |l| |                    +--------+
| |e| +---++---++---+     +---+ |e| |                              
| |s|   .    .    .   .         |s| |                              
| | |   .    .    .    .        | | |                              
| | |   .    .    .     .       | | |                              
| | | +---++---++---+     +---+ | | |                              
| | | |   ||   ||   |     |   | | | |                              
| | | |   ||   ||   |     |   | | | |                              
| | | |   ||   ||   |     |   | | | |                              
| +-+ +---++---++---+     +---+ +-+ |                              
|     +-----------------------+     |                              
|     |      Outer tiles      |     |                              
|     +-----------------------+     |                              
+-----------------------------------+                              
                                                                   
              sNPU Nero                                              
```

# 4. Design parameters

| Name                    | Recommended value         | Role                                    |
| ----------------------- | ------------------------- | --------------------------------------- |
| `NEURON_TILE_COUNT`     | 4~                        | The 'N' in the N by N mesh              |
| `WEIGHT_WIDTH`          | 8/16                      | Synaptic weight width in bits           |
| `DOPAMINE_BUFFER_WIDTH` | 8/16                      | Dopamine buffer width in bits           |
| `E_TRACE_WIDTH`         | 4/8                       | Eligibility trace width in bits         |
| `R_PERIOD_WIDTH`        | 4/8                       | Refractory period width in bits         |
| `COEFFICIENT_WIDTH`     | = `WEIGHT_WIDTH`          | Weight delta coefficient width in bits  |
| `TIMESTAMP_WIDTH`       | 32                        | Timestamp width in bits                 |
| `MAX_CONNECTION`        | `NEURON_TILE_COUNT`^2 / 2 | Maximum fanout connection count         |
| `NEURONS_PER_ROUTER`    | 1~                        | Associated neuron tile count per router |

# 5. Outer tiles considerations

If outer tiles need to communicate with inner tiles, they must support protocol that used on internal tiles. One example is an ingress and egress tile which injects inbound packet and aggregates outbound packets respectively.

# 6. Inner tile composition

As stated on glossary, inner tiles are not directly visible to off-chip components.

## 6.1 Neuron tile

Each neuron tile represents a single spiking neuron.

Neurons only communicate with these inbound and outbound packets. That is, neurons should only have packet interface but nothing else.

### 6.1.1 Packet Format

Regardless of packet protocol, following fields are mandatory:

| Field         | Width                           | Description                                         |
| ------------- | ------------------------------- | --------------------------------------------------- |
| `src_x`       | `ceil(log2(NEURON_TILE_COUNT))` | Source node's `x` coord<br>                         |
| `src_y`       | `ceil(log2(NEURON_TILE_COUNT))` | Source node's `y` coord                             |
| `dest_x`      | `ceil(log2(NEURON_TILE_COUNT))` | Destination node's `x` coord                        |
| `dest_y`      | `ceil(log2(NEURON_TILE_COUNT))` | Destination node's `y` coord                        |
| `timestamp`   | `TIMESTAMP_WIDTH`               | Packet creation timestamp                           |
| `src_type`    | 1                               | Source node's type (Inhibitory/Exhibitory)          |
| `packet_type` | 1                               | Packet type<br>- 1'b0 : Spike<br>- 1'b1 : Control   |
| `ctrl_inst`   | 4                               | Control instruction, *All reserved for future use.* |

It doesn't necessarily have to ship these fields as is. If some protocol can cover these semantically, like combining `src_x` and `src_y` as a `TID` in AXIS, it doesn't matter.

It's then up to implementation details what to append after these mandatory fields. These are considered 'optional' and one possible example could be interface signals like:

| Field    | Width | Description                   |
| -------- | ----- | ----------------------------- |
| `TLAST`  | 1     | Last packet indicator in AXIS |
| `TVALID` | 1     | AXIS Valid signal             |
| `TREADY` | 1     | AXIS Ready signal             |
| ...      |       |                               |
### 6.1.2 Modularized neuron architecture

A neuron tile is designed to be modular, i.e, developers can decide which 'feature' they want to include into their design or not. Each feature comes with their unique code to distinguish themselves from others.

A mandatory feature is marked as (mandatory). Every Nero-based design must implement these to be spec-compliant.

Other optional ones are marked as (optional). Developers can simply opt-out if these do not meet their requirements.

Following RISC-V ISA's convention, developers may denote which feature is implemented in their design by appending a code. For example, 'Potential updates' feature has code named P. If a design only implements it developers can attach a code like for clarity:

> Nero-P

If multiple features were implemented, for example 'Refractory period' as well then:

> Nero-PR

It's advised to append code in order they're listed in specification. 'Potential updates' come first before 'Refractory period', so as shown above it should be 'PR' but not 'RP'.

### 6.1.3 Potential updates (Mandatory, P)

A spiking neuron is a stateful element, which has a time-varing value called membrane potential $V_{mem}$. Given a threshold $V_t$, whenever $V_{mem} \geq V_t$ it fires an outbound packet.

$V_{mem}$ update occurs every clock cycle and follows the [[Leaky Integrate and Fire]], as presented as following ODE. Leak term is applied by a constant coefficient $\tau_{l}$:

$$ \frac{dV_{mem}}{dt} = -\frac{1}{\tau_{l}} [V_{mem}(t) + RI(t)]$$
Where,

- $V_{mem}(t)$ is a membrane potential varying by time $t$
- $I(t)$ is an input current at time $t$ (likely a pulse input)

After emitting a spike packet, $V_{mem}$ is reset to 0. If refractory period exists, refer 6.1.3. Refractory period for more details.

A neuron must maintain a 'weight table' to correctly update $V_{mem}$ from various sources. Whenever a neuron receives a spike, corresponding weight $w$ updates $V_{mem}$. If source is a inhibitory, it decreases the potential by $w$. Increases if it's an exhibitory.

It's an error to receive a spike from a source not registered on such weight table.

### 6.1.4 Refractory period (Optional, R)

After firing a spike, for given a refractory period $T_L$ clock(s) neuron cannot fire a subsequent spikes. $T_L$ is a positive integer which is $T_L \geq 0$.

Two options are possible how $V_{mem}$ should be updated when received a spike during a refractory until it ends:

1. Let no $V_{mem}$ update happen,
2. Or update $V_{mem}$ as usual but do not fire a spike even if it exceeds $V_t$

It's up to implementation what to choose between both.

### 6.1.5 Learning modes (Optional, L)

A neuron tile should support three types of learning method:

1. Frozen (No weight change will ever happen)
2. STDP
3. *DA-STDP (Optional)*

It's an error to set a learning mode not defined in this specification. If this feature is not going to be implemented, it's advised to let weight stay frozen.

Whenever it received or fired a spike, it first initializes the Eligibility trace buffer, $e(t)$ with maximum value. This buffer decays over time exponentially following the below ODE, assuming no external input is present:
$$ \frac{de(t)}{dt} = -\frac{e(t)}{\tau} $$
A recommended decay constant value is $\tau$ = 100 (cycles).

It's then who fired the spike that decreases the weight (LTD) or increases the weight (LTP). 

Weight delta is calculated as follows, as vanilla STDP does:
$$ \delta W = A_{pre} \times G(t) \times e{(t_{post} - t_{pre})} \ (\text{LTP})$$
$$ \delta W = A_{post} \times G(t) \times e(t_{pre} - t_{post}) \ (\text{LTD})$$
where:

- $t$ is a current timestamp
- $G(t)$ is a boolean learning gating function
- $t_{pre}$ is a time when pre-synaptic spike occured
- $t_{post}$ is a time when post-synaptic spike occured
- $A_{pre}$ and $A_{post}$ are weight update coefficient
- $\text{Buffer}$ is a Eligibility trace buffer decays by $t_{pre} - t_{post}$ respectively.

And $G(t)$ is dependent to learning mode:

- For Frozen, $G(t) = 0$ for all time. 
- For STDP, $G(t) = 1$ for all time. 
- For DA-STDP, the value of $G(t)$ is determined by Dopamine buffer.

If expressed in pseudocode:

==TODO: Pseudocode is not right; revise this later==

```
# Global parameter: A_pre, A_post, w_max
# Per synapse: e (Eligiblity trace buffer), w (Weight)

# on each dt:
e *= exp(-dt/tau)

if pre_spike:
	e += A_pre
	w = clip(w + Apost * e, 0, w_max)
if post_spike:
	e += A_post
	w = clip(w + A_pre * e, 0, w_max)
```

### 6.1.6 Dopaminergic neuromodulation (Optional, D)

From another neuron or external intervention, a neuron may receive a dopaminergic neuromodulator. Such neuromodulator has below packet value:

- `packet_type` = 1'b1
- `ctrl_inst` = 4'b1111

Once received, it initializes the dopamine buffer to maximum value. Buffer should decay continuously over time to zero.

How fast such dopamine buffer should decay and should affect to DA-STDP learning method is up to implementation details. One possible implementation is letting dopamine buffer decay within 1,000 clocks upon initialization to zero and let $G(t) = 1$ until buffer hits 0.

### 6.1.7 Implementation recommendations

To fulfill every requirements above, you may consider implementing these:

| Register                     | Width (bit)             | Role                                                                                                                |
| ---------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Membrane potential           | `WEIGHT_WIDTH`          | Stores instantaneous membrane voltage                                                                               |
| Threshold                    | `WEIGHT_WIDTH`          | Stores spike firing threshold                                                                                       |
| Neuron type flag             | 1                       | Stores neuron type, 1'b0 = excitatory, 1'b1 = inhibitory                                                            |
| Learning mode                | 2                       | Stores learning mode,<br>- 2'b00 : Frozen<br>- 2'b01 : STDP<br>- 2'b10 : *DA-STDP (Optional)*<br>- 2'b11 : Reserved |
| Learning gate                | 1                       | Determines whether weight change should happen. Disabled if 0, enabled if 1.                                        |
| Eligibility trace            | `E_TRACE_WIDTH`         | Stores weight change upon pre-/post-spike event. Decays over time (implementation-dependent).                       |
| Refractory period length     | `R_PERIOD_WIDTH`        | Stores refractory period length.                                                                                    |
| LTD weight coefficient       | `COEFFICIENT_WIDTH`     | Stores coefficient for calculating weight change on Long Term Depression (LTD).                                     |
| LTP weight coefficient       | `COEFFICIENT_WIDTH`     | Stores coefficient for calculating weight change on Long Term Potentiation (LTP).                                   |
| *Dopamine buffer (Optional)* | `DOPAMINE_BUFFER_WIDTH` | Gated DA-STDP Buffer, decays over time (implementation-dependent).                                                  |
| Local timer                  | `TIMESTAMP_WIDTH`       | Timer for recording packet timestamp.                                                                               |
| Last spike timer             | `TIMESTAMP_WIDTH`       | Stores 'last spiked time' as a timestamp.                                                                           |

| Memory                | Width (bit)                        | Role                                        |
| --------------------- | ---------------------------------- | ------------------------------------------- |
| Synaptic weight table | `WEIGHT_WIDTH` \* `MAX_CONNECTION` | Synaptic weight from each possible sources. |

## 6.2 Router

A router represents a 'synapse'. It forward spikes toward the destination. Such router exposes five bi-directional ports as presented in table:

| Port | Direction              | Purpose                                                    |
| ---- | ---------------------- | ---------------------------------------------------------- |
| N    | North                  | Connects to the router whose grid coordinate is $(x, y+1)$ |
| E    | East                   | Connects to the router whose grid coordinate is $(x+1,y)$  |
| W    | West                   | Connects to the router whose grid coordinate is $(x-1,y)$  |
| S    | South                  | Connects to the router whose grid coordinate is $(x,y-1)$  |
| T    | Local (to/from neuron) | Interface to associated neuron tile (neuron-router link)   |

**Visualized port**

```
             (x,y+1)                
                N                   
          +------------+            
          |            |            
          |            |            
          |            |            
(x-1,y) W |   Router   | E (x+1,y)  
          |            |            
          |            |            
          |            |            
          +------------+            
                S      ^ T (Local)       
             (x,y-1)   |            
                       +-->+---+    
                           |   |    
                           |   |    
                           |   |    
                           +---+    
                         Neuron tile
```

### 6.2.1 Spike routing scheme

When a router received a spike, it should forward spike to one of available ports. An outbound port is 'available' if the downstream routers are not stalled, mostly when their FIFO is not full. A router shall stall inbound spike traffic if no available output port exists.

Every router must maintain a 'routing table' that maps an incoming spike to the next-hop direction. Such routing table must be either: 

1. Forward spike to any of cardinal direction port
2. Or to local port only. 

It's an error to allow both cases at once.

When choosing a port, following rules apply:

1. Only choose ports prescribed on router table.
2. If it's set to cardinal direction, pick a port by following order: East > West > North  > South. East port has the highest priority and South port has the lowest priority. If it's local, then only a local port is selected.
3. If first candidate from 2. is unavailable right now, select the next available one.
4. If none of the ports are available, wait until the neighbor flags itself as 'ready'.

**Example**
Given a spike coming from $(3, 4)$ and routing table says 'North' and 'South', a router should redirect spike to north port. However if such port is unavailable because a neighbor is busy, then it chooses the next, south port. If none of them are available, router waits until one of ports become available again.

When forwarding a spike, it can be queued or stalled but it **MUST NOT** be dropped under any circumstances. A FIFO *may* be placed on the inbound path of each port to buffer bursts of spikes that arrive while a downstream port is stalled.

It's an error to receive spike from neuron whose grid location is not registered on routing table.

### 6.2.2 Delay considerations

Except an autapse (a neuron is connected to itself), it's worth note that neuron to neuron spikes take some cycles to arrive.

This is up to implementation, but normally it's expected that a baseline latency, a minimum required clock to arrive a destination, $L$ is calculated as: $$L = 2 + D_H $$ $D_H$ is a number of router hops between the source and the destination, which is the number of router boundaries crossed. The constant 2 accounts for round-trip latency: one clock for source tile -> router forwarding and another for router -> destination tile.

It's worth knowing that in practice, back-pressure or buffering may add extra cycles, but the system must still guarantee that the spike eventually reaches its destination.

### 6.2.3 Arbitrating multiple outbound spikes

If more than a single spike have to go out through a port at the same time, a router must decide which spike should be forwarded first until there are no pending spikes remaining.

The arbitration scheme is implementation-dependent, but such implementation must guarantee that no deadlock would occur. Also, dropping a spike on arbitration is **strictly forbidden.** It's recommended to use deterministic and bounded method like round-robin for predictable results.

### 6.2.4 Multiple neuron tiles (Optional, M)

A router may have more than a single neuron tile. To distinguish a destination among associated neurons, the spike packet must carry following field:

| Field            | Width                                 | Description           |
| ---------------- | ------------------------------------- | --------------------- |
| `src_neuron_id`  | `ceil(log2(NEURON_TILES_PER_ROUTER))` | Source neuron id      |
| `dest_neuron_id` | `ceil(log2(NEURON_TILES_PER_ROUTER))` | Destination neuron id |

As routers have to forward spikes to corresponding destination, addition to 6.2.1 Spike routing scheme:

1. If `dest_x` and `dest_y` is equal to router's `x` and `y`,
		a. For each local port, send spike to port that `dest_neuron_id` == `id`.
2. Otherwise, follow 6.2.1's Spike routing scheme.

It's an error to receive a spike which contains `dest_neuron_id` that does not exist on router. For example, it's invalid to receive a spike with `dest_neuron_id` = 3 when there's only two neurons associated with a router.

### 6.2.5 Spike replication (Optional, Rp)

Upon lookup, if a router identified that incoming spike have multiple destination and can be distributed toward more than a single port, router *may* replicate the spike to efficiently deal with heavy fan-out case.

For example, if spike arrived at router located on $(2, 0)$ has multiple destinations: $(3, 0)$, $(1, 0)$, $(2, 1)$ and $(2, -1)$ then router can fire four spikes at once toward N, E, W, S cardinal direction instead of firing spikes one at a time.

### 6.3 Error handling

Whenever error occurs, how to deal with these is implement-dependent. You can:

1. Just set an error flag and proceed so host can figure out error has occured later,
2. Or record an error to designated FIFO for detailed analysis,
3. Or shut down such neuron/router immediately, make it frozen before things go wrong.
