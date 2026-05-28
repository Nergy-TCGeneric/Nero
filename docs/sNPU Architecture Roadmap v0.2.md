---
created: 2025-10-24 02:07
modified: 2026-01-27 12:42
---
# Outlining sNPU Specification

- [x] Dopaminergic neuromodulation with pre-defined initialized value (concentration)
- [x] Control commands (set/get weight, neuron type, ...)
	- [x] Configurable routes?
	- [x] Debugging commands (step/run/stop)
- [x] Allowing multiple neuron tiles for each router

# Implementation

## Hardware

**Implementation note**:

Do NOT ever try mixing DNN's approach with hardware. sNPU is optimized for sparse, time-delay aware, cyclic computation. In other words, its only objective is:

> Accelerate SNN models, faster than CPU.

- [ ] `Nero-P` compliant(Mem. Potential Update) device
	- [ ] Use simulation to verify its behavior
	- Shipping this to real hardware is less useful as host cannot reliably know what's going on the machine.
- [ ] `Nero-PT` compliant(+ Trace Logging) device
	- [ ] Use simulation to verify its behavior
	- [ ] Implement in real hardware (Is this design FPGA-verified?)
	- Bare minimum to use on real life, at least it's traceable on host realtime.
- [ ] `Nero-PLT` compliant(+ Learning Capability) device
	- [ ] Use simulation to verify its behavior
	- [ ] Implement in real hardware
	- [ ]  Use [[Morphogenetic search engine in Nero|Morphogenetic Search Engine]] to find interesting working candidate on spike-variant [[FrozenLake]] environment
		- May require frequent re-implementation on  FPGA side, but it's acceptable at this point until `Nero-PLTC` is implemented
- [ ] `Nero-PLTC` compliant (+ Dynamic Connection) device
	- [ ] Use simulation to verify its behavior
	- [ ] Implement in real hardware

## Nero Synthesizer

**Implementation note**:

Nero Synthesizer does NOT optimize by itself. Rather, this does one thing: 

> Place neurons and connect them on sNPU, whatever it takes.

### After `Nero-P` compliant device implementation
- [ ] **Graph to grid tile converter** (Placement)
	- From supplied user's arbitrary graph topology.
- [ ] **A basic, random topology generator** based on user's constraint
	- Total neuron count
	- Exhibitory - Inhibitory Rate
- [ ] **A memory file generator** that can be fed into sNPU Nero with `$readmemh()` function
	- Used when re-baking weight/connections on sNPU later, ahead of time.
### After `Nero-PT` compliant device implementation
- [ ] **Establish file ABI**, so [[Morphogenetic search engine in Nero|Morphogenetic search engine]] can interact with.
	- [ ] Add a deserialization/serialization feature.
	- Note that this serialized file acts as a 'snapshot'.
- [ ] **Model partitioning API**
	- [ ] Slice the sNPU logically, allocate a space for each model for parallelization based on user configuration.
		- How much partitions? How many neurons?

## [[Petricia]]

**Implementation note:**

1. Unlike Narrower search engine, its prime objective is finding (multiple) 'promising' model. These may be suboptimal, but it's not necessarily this engine's responsibility to optimize these. Users may want to use narrower engine and morphogenetic engine alternately to get a better result.
2. When exploring those candidates, changing hyperparameters should be a last resort when everything fails, like neuron count.
3. Consider having some generous neuron and synpase connections at the beginning. Newborn brains' connection explode at neurogenesis phase and pruned out as time progresses.

### After `Nero-PT` compliant device implementation
- [ ] **SerDes interface**, based on Synthesizer file ABI.
	- [ ] Import the topology from deserialized content.
	- [ ] Export the optimized topology with ABI-compliant serialized content.
- [ ] **Post-hoc packet analysis**
	- [ ] **Neuron placement analysis**
		- **Identify the traffic hotspot**, based on their causal connection based on spike packet flow
	- [ ] **Neuron activity analysis**
		- Find how much this neuron 'spiked' throughout the given time window $\delta t$.
		- Should be done together with saliency analysis. Mark neurons 'prunable' if it rarely fires spike and has less saliency.
	- [ ] **Neuron saliency analysis**
		- Based on temporal spike data flow graph, calculate the 'significance' of each neuron.
	- [ ] **Neuron stability analysis**
		- Based on spike intervals (or any patterns observable), calculate how often this neuron have been exhibiting 'stable' spike patterns over time.
 - [ ] **Evolution-based neuron model search**
	 - [ ] Based on post-hoc packet analysis, generate a serialized file that contains next candidates for subsequent iteration.
	 - It's not continuous at this moment, as Nero Synthesizer does not support dynamic reconfiguration, but at least it can form a closed loop.

## [[Chronos (Nero)]]

**Implementation note:**

1. sNPU mandates every multi-flit packets like logs must arrive to destination in order. Be sure to preserve their causal link by sorting them out first with source field and list them up with their relative timestamp.

### After `Nero-PT` compliant device implementation
- [ ] **SerDes interface**, based on Synthesizer file ABI.
	- [ ] Import the topology from deserialized content.
- [ ] **Complete/Partial runtime reconstruction**
	- [ ] Based on trace logs available, Reconstruct the runtime visually from the beginning or at certain point.

## [[Hermes (Nero)]]

After `Nero-PT` compliant device implementation
- [ ] **SerDes interface**, based on Synthesizer file ABI.
	- [ ] Import the spike stream from deserialized content. (Presumably from flight recorder)
- [ ] **Spike pattern analysis**
	- [ ] From trace log, extract temporal spike stream patterns.
	- [ ] Pick N pattern, among the most confident ones.
- [ ] **Semantic labeling**
	- [ ] Add a labeling feature where researchers can label each spike streams
- [ ] **Spike pattern comparison**
	- [ ] Run a neighboring pattern comparison, calculate the similarity
	- [ ] Show whether two patterns are similar or not (under threshold?)

## [[Caesar (Nero)]]

**Implementation Note**

1. sNPU cannot help this task. Consider guiding users utilize CPU/GPU(or anything can accelerate MatMul) here as gradient descent is a dense operation.
2. Vanilla [[Backpropagation]] requires computation graph to be acyclic. Consider using cycle-friendly algorithm like BPTT for precision or other computation-cheap ones.

After `Nero-PT` compliant device implementation
- [ ] **SerDes interface**, based on Synthesizer file ABI.
	- [ ] Import the network topology from deserialized content.
	- [ ] Import the spike streams (output), act as a 'golden output'
- [ ] **Optimization via [[Surrogated Gradient]] Descent**
	- [ ] Use spikes to calculate loss and gradient

## [[Proteus (Nero)]]