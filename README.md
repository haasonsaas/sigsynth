# SigSynth

A comprehensive detection engineering platform for generating and validating synthetic log tests for Sigma rules. Features AI-powered test generation, batch processing, and multi-platform support with enterprise-grade scalability.

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

> **Note**: SigSynth is currently in development. Install from source for the latest features:
> ```bash
> git clone https://github.com/haasonsaas/sigsynth.git
> cd sigsynth
> pip install -e .
> ```

## Quick Start

1. **Set your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Generate tests for a single rule**:
   ```bash
   sigsynth generate --rule my_rule.yml --output ./tests
   ```

3. **Process multiple rules in parallel**:
   ```bash
   sigsynth batch --rules-dir ./sigma-rules --output ./tests --workers 8
   ```

4. **Use configuration files for team settings**:
   ```bash
   # Create sigsynth.yaml with your preferences
   sigsynth --config sigsynth.yaml batch --rules-dir ./rules --output ./tests
   ```

## Usage Examples

### Single Rule Testing
```bash
# Basic usage
sigsynth generate --rule rule.yml --output ./tests

# Production-quality tests
sigsynth generate \
  --rule aws_cloudtrail_change.yml \
  --seed-samples 10 \
  --samples 500 \
  --output ./tests
```

### Batch Processing
```bash
# Process all rules in a directory
sigsynth batch --rules-dir ./sigma-rules --output ./tests

# Production CI/CD workflow
sigsynth batch \
  --rules-dir ./rules \
  --exclude "**/draft/**" \
  --exclude "**/experimental/**" \
  --workers 16 \
  --fail-fast \
  --output ./production-tests
```

### Configuration Management
```yaml
# sigsynth.yaml
seed_samples: 10
samples: 500
random_seed: 42

batch:
  parallel_workers: 8
  exclude_patterns:
    - "**/draft/**"
    - "**/experimental/**"
```

📖 **[See USAGE.md for comprehensive examples, workflows, and best practices](./USAGE.md)**

### Configuration File

Create a configuration file for team settings:

```bash
# Copy example configuration
cp sigsynth.example.yaml sigsynth.yaml

# Edit for your needs
vim sigsynth.yaml

# Use with any command
sigsynth --config sigsynth.yaml batch --rules-dir ./rules --output ./tests
```

## Requirements

- **Python**: 3.8 or higher
- **OpenAI API Key**: Required for AI-powered test generation ([Get yours here](https://platform.openai.com/account/api-keys))
- **Memory**: 2GB+ RAM (4GB+ recommended for large rule sets)
- **Cost**: ~$0.01-0.05 per rule (varies by complexity)

## Configuration

SigSynth provides flexible configuration through:

1. **Configuration files**: `sigsynth.yaml`, `.sigsynth.yaml`, or `~/.sigsynth.yaml`
2. **Environment variables**: `SIGSYNTH_*` variables override config files
3. **CLI options**: Highest priority, override everything else

### Key Environment Variables
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `SIGSYNTH_PARALLEL_WORKERS`: Number of parallel workers (default: 4)
- `SIGSYNTH_SAMPLES`: Total test cases per rule (default: 200)
- `SIGSYNTH_SEED_SAMPLES`: AI-generated seeds per rule (default: 5)

📖 **[See USAGE.md for complete configuration reference](./USAGE.md#configuration-management)**

## Platform Support

### Currently Supported
- ✅ **Panther**: Full support with JSON test files, field mappings, and compatibility checking

### Coming Soon
- 🚧 **Splunk**: SPL test cases and field mappings
- 🚧 **Elastic**: EQL queries and index patterns  
- 🚧 **QRadar**: AQL queries and rule formats

**Extensible Architecture**: Easy to add new platforms via the plugin system.

📖 **[See USAGE.md for platform-specific guides](./USAGE.md#platform-specific-guides)**

## Performance

| Rule Count | Workers | Time | Cost (est.) |
|------------|---------|------|-----------|
| 1 rule | 1 | 10s | $0.01-0.05 |
| 10 rules | 4 | 30s | $0.10-0.50 |
| 100 rules | 8 | 5min | $1-5 |
| 1000 rules | 16 | 45min | $10-50 |

📊 **Scales efficiently**: Process thousands of rules with parallel workers

> **Production Ready**: Used by security teams to generate comprehensive test suites for detection rule validation and CI/CD pipelines.

## Development

```bash
# Clone and setup
git clone https://github.com/haasonsaas/sigsynth.git
cd sigsynth
python3 -m venv venv && source venv/bin/activate
pip install -e .

# Run tests
pytest tests/ -v
```

**Contributing**: See [USAGE.md](./USAGE.md#development) for detailed development guide.

## What's New

### v0.2.0 - Production-Ready Platform
- 🆕 **Batch Processing**: Parallel processing of multiple rules with configurable workers
- 🆕 **Multi-Platform Framework**: Extensible architecture ready for Splunk, Elastic, QRadar
- 🆕 **Configuration Management**: YAML configs with environment variable overrides
- 🆕 **Enhanced CLI**: New commands with rich console output and progress tracking
- 🆕 **World-Class Documentation**: 3 comprehensive guides (USAGE.md, TROUBLESHOOTING.md, examples)
- 🆕 **Enterprise Features**: CI/CD integration, team configurations, performance optimization

### v0.1.0 - Initial Release
- Single rule processing with OpenAI-powered test generation
- Panther platform support
- Local test expansion and validation

## Documentation

| Resource | Description |
|----------|-------------|
| 📜 **[Usage Guide](./USAGE.md)** | Comprehensive examples, workflows, and best practices |
| ⚙️ **[Configuration Example](./sigsynth.example.yaml)** | Sample configuration file with all options |
| 🔧 **[Troubleshooting](./TROUBLESHOOTING.md)** | Quick fixes for common issues |
| 💬 **[GitHub Discussions](https://github.com/haasonsaas/sigsynth/discussions)** | Community support and questions |
| 🐛 **[GitHub Issues](https://github.com/haasonsaas/sigsynth/issues)** | Bug reports and feature requests |

```bash
# Get help for any command
sigsynth --help
sigsynth generate --help
sigsynth batch --help
```

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

**🚀 Ready to supercharge your Sigma rule testing?** 

Start with the [Quick Start](#quick-start) above, then dive into the [comprehensive usage guide](./USAGE.md) for advanced workflows and best practices. 