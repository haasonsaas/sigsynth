# SigSynth

Generates synthetic log test cases for Sigma rules using OpenAI. Processes single rules or batches of rules with parallel workers and outputs test cases for multiple SIEM platforms.

## Features

- Single rule processing and batch processing with parallel workers
- Multi-platform support: Panther, Splunk, Elastic
- AI-powered seed generation using OpenAI
- Local test expansion to minimize API costs
- Rule validation with detailed error reporting
- Debug mode with rule analysis and complexity metrics
- Configuration management via files and environment variables

## Installation

```bash
pip install sigsynth
```

Development installation:
```bash
git clone https://github.com/haasonsaas/sigsynth.git
cd sigsynth
pip install -e .
```

## Quick Start

1. Set OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

2. Generate tests for a single rule:
   ```bash
   sigsynth generate --rule rule.yml --output ./tests
   ```

3. Process multiple rules:
   ```bash
   sigsynth batch --rules-dir ./rules --output ./tests
   ```

## Commands

### generate
Generate test cases for a single Sigma rule.

```bash
sigsynth generate --rule rule.yml --platform panther --output ./tests
```

Options:
- `--rule`: Path to Sigma rule file (required)
- `--platform`: Target platform (panther, splunk, elastic)
- `--seed-samples`: Number of seed samples per type (default: 5)
- `--samples`: Total test samples to generate (default: 200)
- `--output`: Output directory (required)
- `--random-seed`: Random seed for reproducible results

### batch
Process multiple Sigma rules in parallel.

```bash
sigsynth batch --rules-dir ./rules --output ./tests --workers 8
```

Options:
- `--rules-dir`: Directory containing Sigma rules (required)
- `--pattern`: File patterns to match (can specify multiple)
- `--exclude`: Patterns to exclude (can specify multiple)
- `--platform`: Target platforms (can specify multiple)
- `--output`: Output directory (required)
- `--workers`: Number of parallel workers
- `--fail-fast`: Stop on first error

### debug
Analyze rule processing and test generation.

```bash
sigsynth debug --rule rule.yml --trace
```

Options:
- `--rule`: Path to Sigma rule file (required)
- `--test-case`: Specific test case index to debug
- `--trace`: Enable detailed tracing
- `--output`: Save debug report to file

## Configuration

Configuration priority: CLI options > environment variables > config files

### Config File
Create `sigsynth.yaml`:

```yaml
seed_samples: 10
samples: 500
random_seed: 42

platforms:
  panther:
    name: panther
    output_format: json
  splunk:
    name: splunk
    output_format: spl
  elastic:
    name: elastic
    output_format: json

batch:
  input_patterns:
    - "**/*.yml"
    - "**/*.yaml"
  exclude_patterns:
    - "**/draft/**"
    - "**/experimental/**"
  parallel_workers: 8
  fail_fast: false

debug:
  enabled: false
  verbose: false
  trace_validation: false
```

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key (required)
- `SIGSYNTH_PARALLEL_WORKERS`: Number of parallel workers
- `SIGSYNTH_SAMPLES`: Total test cases per rule
- `SIGSYNTH_SEED_SAMPLES`: AI-generated seeds per rule
- `SIGSYNTH_DEBUG`: Enable debug mode

## Platform Support

### Panther
- Output: JSON test files
- Features: Field mapping validation, compatibility checking
- Structure: Individual test files + manifest

### Splunk
- Output: SPL queries + NDJSON data
- Features: Sourcetype detection, field mapping suggestions
- Structure: Search file + test data + manifest

### Elastic
- Output: JSON documents with ECS mapping
- Features: Bulk import format, index templates
- Structure: Bulk NDJSON + individual documents + manifest

## Performance

| Rules | Workers | Time | API Cost |
|-------|---------|------|----------|
| 1     | 1       | 10s  | $0.01-0.05 |
| 10    | 4       | 30s  | $0.10-0.50 |
| 100   | 8       | 5min | $1-5 |
| 1000  | 16      | 45min| $10-50 |

## Requirements

- Python 3.8+
- OpenAI API key
- 2GB+ RAM (4GB+ for large rule sets)

## Development

```bash
git clone https://github.com/haasonsaas/sigsynth.git
cd sigsynth
python3 -m venv venv && source venv/bin/activate
pip install -e .
pytest tests/ -v
```

## Documentation

- [USAGE.md](./USAGE.md) - Comprehensive usage guide
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues
- [sigsynth.example.yaml](./sigsynth.example.yaml) - Configuration example

## License

MIT - see [LICENSE](./LICENSE)