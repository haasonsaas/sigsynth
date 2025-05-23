# SigSynth

A tool for generating and validating synthetic log tests for Sigma rules against Panther, using a single OpenAI call per rule and local expansion for edge-case coverage.

## Features

- **Single Rule Processing**: Generate test cases for individual Sigma rules
- **Batch Processing**: Process multiple rules in parallel with configurable workers
- **Multi-Platform Support**: Extensible platform framework (currently supports Panther)
- **Configuration Management**: File-based and environment variable configuration
- **AI-Powered Seed Generation**: Generate realistic positive and negative test seeds using OpenAI
- **Local Test Expansion**: Create test variants locally to maximize coverage while minimizing API costs
- **Rule Validation**: Validate tests against rule logic with detailed error reporting
- **Debug Mode**: Detailed tracing and debugging capabilities (coming soon)

## Installation

```bash
pip install sigsynth
```

## Usage

### Single Rule Generation

```bash
sigsynth generate \
  --rule aws_cloudtrail_change.yml \
  --platform panther \
  --seed-samples 5 \
  --samples 200 \
  --output panther_tests/
```

### Batch Processing

```bash
# Process all rules in a directory
sigsynth batch \
  --rules-dir ./sigma-rules \
  --output ./tests \
  --workers 8

# Process with custom patterns and multiple platforms
sigsynth batch \
  --rules-dir ./rules \
  --pattern "**/*.yml" \
  --exclude "draft/**" \
  --platform panther \
  --output ./tests
```

### Configuration File

Create a `sigsynth.yaml` file for default settings:

```yaml
seed_samples: 10
samples: 500
random_seed: 42

platforms:
  panther:
    name: panther
    output_format: json

batch:
  input_patterns:
    - "**/*.yml"
    - "**/*.yaml"
  exclude_patterns:
    - "**/draft/**"
  parallel_workers: 8
  fail_fast: false
```

Then run with configuration:

```bash
sigsynth --config sigsynth.yaml batch --rules-dir ./rules --output ./tests
```

## Requirements

- Python 3.8+
- OpenAI API key (set via OPENAI_API_KEY environment variable)

## Configuration

SigSynth can be configured through:

1. **Configuration files**: `sigsynth.yaml` in current directory or `~/.sigsynth.yaml`
2. **Environment variables**: `SIGSYNTH_SEED_SAMPLES`, `SIGSYNTH_PARALLEL_WORKERS`, etc.
3. **Command-line options**: Override any setting via CLI flags

### Environment Variables

- `OPENAI_API_KEY`: OpenAI API key (required)
- `SIGSYNTH_SEED_SAMPLES`: Number of seed samples per type
- `SIGSYNTH_SAMPLES`: Total number of test samples
- `SIGSYNTH_PARALLEL_WORKERS`: Number of parallel workers for batch processing
- `SIGSYNTH_DEBUG`: Enable debug mode

## Platforms

Currently supported platforms:

- **Panther**: JSON test files compatible with Panther's Rules SDK

Coming soon:
- **Splunk**: SPL (Search Processing Language) test cases
- **Elastic**: EQL (Event Query Language) test cases
- **QRadar**: AQL (Ariel Query Language) test cases

## Development

1. Clone the repository
2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install in development mode:
   ```bash
   pip install -e .
   ```
4. Run tests:
   ```bash
   pytest
   ```

## License

MIT 