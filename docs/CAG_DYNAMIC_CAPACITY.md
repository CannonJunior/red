# CAG Dynamic Capacity Configuration

## Overview

The Cache-Augmented Generation (CAG) system automatically determines its optimal token capacity based on your system's available memory. This ensures efficient resource utilization across different hardware configurations without manual tuning.

## How It Works

### Automatic Detection (Default)

When you initialize the CAG system without specifying a capacity, it automatically:

1. **Detects System Memory**: Reads total and available RAM
2. **Calculates Usable Memory**: Reserves memory for OS and other processes
3. **Estimates Token Capacity**: Converts available memory to token count
4. **Applies Constraints**: Caps at model limits and ensures minimum usability

### Calculation Formula

```python
# Reserve memory for system (25% of total RAM or 2GB minimum)
reserved_ram = max(2.0 GB, total_ram * 0.25)

# Calculate usable RAM for CAG
usable_ram = available_ram - reserved_ram

# Convert to tokens (assuming 6 bytes per token)
estimated_tokens = usable_ram / 6 bytes

# Apply constraints
optimal_tokens = max(32,000, min(estimated_tokens, 200,000))
```

### Memory Estimation

The system estimates **6 bytes per token** based on:
- Text storage: ~4 bytes per token
- Metadata overhead: ~1 byte per token
- Python object overhead: ~1 byte per token

## Usage

### Automatic Capacity (Recommended)

```python
from cag_api import CAGManager

# Automatically detects optimal capacity
manager = CAGManager()
```

### Custom Capacity

```python
from cag_api import CAGManager

# Use a specific capacity (useful for testing or special requirements)
manager = CAGManager(max_context_tokens=64_000)
```

### Check Calculated Capacity

```python
from cag_api import calculate_optimal_cag_capacity

# Get the capacity that would be used
optimal_capacity = calculate_optimal_cag_capacity()
print(f"Your system's optimal CAG capacity: {optimal_capacity:,} tokens")
```

## Capacity Guidelines

### By System Type

| System Type       | RAM   | Typical Capacity | Notes                          |
|-------------------|-------|------------------|--------------------------------|
| Low-end laptop    | 4 GB  | 32,000 tokens    | Minimum for basic usage        |
| Mid-range laptop  | 8 GB  | 200,000 tokens   | Good for most documents        |
| High-end laptop   | 16 GB | 200,000 tokens   | Capped at model limit          |
| Workstation       | 32 GB | 200,000 tokens   | Capped at model limit          |
| Server            | 64 GB | 200,000 tokens   | Capped at model limit          |

### Model Context Window Limits

The system respects modern LLM context window limits:

- **Maximum**: 200,000 tokens (Claude 3, GPT-4 Turbo, etc.)
- **Minimum**: 32,000 tokens (for basic usability)

Even if your system has sufficient RAM for more tokens, the capacity is capped at the model's maximum context window.

## Testing

Run the test script to see your system's calculated capacity:

```bash
PYTHONPATH=/home/junior/src/red uv run test_cag_capacity.py
```

This will show:
- Your system's memory information
- Calculated optimal capacity
- Estimated memory usage
- Capacity estimates for different system configurations

## Advantages

### 1. Zero Configuration
No manual tuning required - works optimally on any hardware

### 2. Resource Efficiency
Automatically adapts to available memory without over-allocation

### 3. Predictable Performance
Ensures consistent behavior across different deployments

### 4. Future-Proof
Automatically adjusts when:
- System memory changes
- Model context windows expand
- System load varies

## Technical Details

### Logging

The CAG system logs detailed capacity calculation information:

```
INFO:cag_api:CAG Capacity Calculation:
  Total RAM: 28.17 GB
  Available RAM: 17.70 GB
  Usable for CAG: 10.66 GB
  Estimated tokens: 1,906,949,461
  Optimal capacity: 200,000 tokens

INFO:cag_api:CAG Manager initialized with 200,000 token capacity
```

### Dependencies

- `psutil`: System and process utilities (for memory detection)
- `tiktoken`: OpenAI's token counting library

### Error Handling

If automatic detection fails (e.g., psutil not available), the system falls back to a safe default of 128,000 tokens:

```
WARNING:cag_api:Failed to calculate optimal CAG capacity: <error>. Using default 128K.
```

## Configuration Override

To override the automatic calculation in `server.py`:

```python
from cag_api import CAGManager

# Force a specific capacity
cag_manager = CAGManager(max_context_tokens=100_000)
```

## Best Practices

1. **Use Auto-Detection**: Let the system determine optimal capacity
2. **Monitor Usage**: Check the CAG Knowledge dashboard for memory utilization
3. **Clear Cache**: Remove unused documents to free up capacity
4. **Test Locally**: Run the test script to verify capacity on your system

## RED Compliance

This feature aligns with RED principles:

- ✅ **COST-FIRST**: Zero-cost automatic optimization
- ✅ **LOCAL-FIRST**: No external API calls for detection
- ✅ **SIMPLE-SCALE**: Optimized for 5 users without manual tuning
- ✅ **AGENT-NATIVE**: Dynamic adaptation to agent workload

## Future Enhancements

Potential improvements:
- Dynamic capacity adjustment based on real-time memory pressure
- Per-workspace capacity allocation
- Memory usage predictions based on document size
- Integration with system monitoring tools
