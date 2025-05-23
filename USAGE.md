# SigSynth - Comprehensive Usage Guide

This guide provides detailed instructions for using SigSynth in real-world scenarios, from single rule testing to large-scale batch processing.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Single Rule Generation](#single-rule-generation)
3. [Batch Processing](#batch-processing)
4. [Configuration Management](#configuration-management)
5. [Advanced Workflows](#advanced-workflows)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Performance Optimization](#performance-optimization)
9. [Platform-Specific Guides](#platform-specific-guides)

## Quick Start

### 1. Set Your OpenAI API Key
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Generate Tests for a Single Rule
```bash
sigsynth generate --rule my_rule.yml --output ./tests
```

### 3. Process Multiple Rules
```bash
sigsynth batch --rules-dir ./sigma-rules --output ./tests
```

## Single Rule Generation

The `generate` command creates test cases for individual Sigma rules.

### Basic Usage

```bash
# Minimal command - uses default settings
sigsynth generate --rule rule.yml --output ./tests

# Full options
sigsynth generate \
  --rule aws_cloudtrail_change.yml \
  --platform panther \
  --seed-samples 5 \
  --samples 200 \
  --random-seed 42 \
  --output ./tests
```

### Real-World Examples

**AWS CloudTrail Rule**:
```bash
# Generate comprehensive tests for CloudTrail rules
sigsynth generate \
  --rule rules/aws/cloudtrail_config_change.yml \
  --seed-samples 10 \
  --samples 500 \
  --output tests/aws/cloudtrail/
```

**Windows Security Rule**:
```bash
# Generate tests for Windows event logs
sigsynth generate \
  --rule rules/windows/process_injection.yml \
  --seed-samples 8 \
  --samples 300 \
  --output tests/windows/
```

**Network Security Rule**:
```bash
# Generate tests for network-based detections
sigsynth generate \
  --rule rules/network/suspicious_dns.yml \
  --seed-samples 6 \
  --samples 250 \
  --output tests/network/
```

## Batch Processing

The `batch` command processes multiple rules efficiently with parallel workers.

### Basic Batch Processing

```bash
# Process all YAML files in a directory
sigsynth batch --rules-dir ./sigma-rules --output ./tests

# Use more workers for faster processing
sigsynth batch \
  --rules-dir ./sigma-rules \
  --output ./tests \
  --workers 16
```

### Advanced Batch Processing

**Selective Processing with Patterns**:
```bash
# Process only AWS rules
sigsynth batch \
  --rules-dir ./sigma-rules \
  --pattern "**/aws/**/*.yml" \
  --output ./tests/aws

# Process multiple patterns
sigsynth batch \
  --rules-dir ./sigma-rules \
  --pattern "**/windows/**/*.yml" \
  --pattern "**/linux/**/*.yml" \
  --exclude "**/experimental/**" \
  --exclude "**/deprecated/**" \
  --output ./tests
```

**Production Rule Processing**:
```bash
# Process production rules with fail-fast for CI/CD
sigsynth batch \
  --rules-dir ./production-rules \
  --exclude "**/draft/**" \
  --exclude "**/test/**" \
  --exclude "**/*.disabled.yml" \
  --workers 12 \
  --fail-fast \
  --output ./production-tests
```

**Multi-Platform Generation** (when available):
```bash
# Generate tests for multiple platforms
sigsynth batch \
  --rules-dir ./rules \
  --platform panther \
  --platform splunk \
  --platform elastic \
  --output ./multi-platform-tests
```

## Configuration Management

SigSynth supports flexible configuration through files, environment variables, and CLI options.

### Configuration File Setup

Create a `sigsynth.yaml` file in your project root:

```yaml
# Global test generation settings
seed_samples: 10          # More seeds = better coverage
samples: 500             # More samples = more test cases
random_seed: 42          # For reproducible results

# Platform configurations
platforms:
  panther:
    name: panther
    output_format: json
    custom_options:
      test_prefix: "test_"
      include_metadata: true
      generate_manifest: true

# Batch processing settings
batch:
  input_patterns:
    - "**/*.yml"
    - "**/*.yaml"
  exclude_patterns:
    - "**/draft/**"
    - "**/experimental/**"
    - "**/*.disabled.yml"
    - "**/test/**"
  parallel_workers: 8      # Adjust based on your CPU cores
  fail_fast: false        # Set to true for CI/CD

# Debug and development settings
debug:
  enabled: false
  verbose: false
  trace_validation: false
```

### Team Configuration

For team environments, create different configs for different scenarios:

**Development Config (`dev.yaml`)**:
```yaml
seed_samples: 3
samples: 100
batch:
  parallel_workers: 4
  fail_fast: false
debug:
  enabled: true
  verbose: true
```

**Production Config (`prod.yaml`)**:
```yaml
seed_samples: 15
samples: 1000
random_seed: 42
batch:
  parallel_workers: 16
  fail_fast: true
debug:
  enabled: false
```

**CI/CD Config (`ci.yaml`)**:
```yaml
seed_samples: 5
samples: 200
batch:
  parallel_workers: 8
  fail_fast: true
debug:
  enabled: false
```

Then use them:
```bash
# Development
sigsynth --config dev.yaml batch --rules-dir ./rules --output ./dev-tests

# Production
sigsynth --config prod.yaml batch --rules-dir ./rules --output ./prod-tests

# CI/CD
sigsynth --config ci.yaml batch --rules-dir ./changed-rules --output ./ci-tests
```

### Environment Variables

Set environment variables for system-wide or CI/CD configuration:

```bash
# Required
export OPENAI_API_KEY="your-api-key"

# Optional overrides
export SIGSYNTH_SEED_SAMPLES=10
export SIGSYNTH_SAMPLES=500
export SIGSYNTH_PARALLEL_WORKERS=16
export SIGSYNTH_DEBUG=true

# Then run without specifying these options
sigsynth batch --rules-dir ./rules --output ./tests
```

## Advanced Workflows

### Continuous Integration

**GitHub Actions Example**:
```yaml
name: Generate Sigma Tests
on:
  push:
    paths: ['rules/**/*.yml']

jobs:
  test-generation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install SigSynth
        run: pip install sigsynth
      
      - name: Generate Tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          sigsynth --config .sigsynth/ci.yaml batch \
            --rules-dir ./rules \
            --output ./generated-tests \
            --fail-fast
      
      - name: Upload Test Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: sigma-tests
          path: generated-tests/
```

**GitLab CI Example**:
```yaml
generate-tests:
  stage: test
  image: python:3.11
  before_script:
    - pip install sigsynth
  script:
    - sigsynth --config ci.yaml batch --rules-dir ./rules --output ./tests --fail-fast
  artifacts:
    paths:
      - tests/
    expire_in: 1 week
  only:
    changes:
      - rules/**/*.yml
```

### Rule Development Workflow

1. **Create a new rule**:
   ```bash
   # Create rule file
   vim rules/aws/new_attack_pattern.yml
   ```

2. **Generate initial tests**:
   ```bash
   sigsynth generate \
     --rule rules/aws/new_attack_pattern.yml \
     --seed-samples 5 \
     --samples 100 \
     --output tests/development/
   ```

3. **Review and refine**:
   ```bash
   # Check generated test cases
   ls tests/development/
   cat tests/development/test_manifest.json
   
   # Review specific test cases
   cat tests/development/test_001.json | jq .
   ```

4. **Generate production tests**:
   ```bash
   sigsynth --config prod.yaml generate \
     --rule rules/aws/new_attack_pattern.yml \
     --output tests/production/
   ```

### Large-Scale Rule Processing

**Processing 1000+ Rules**:
```bash
# Use maximum parallelism and optimize for throughput
sigsynth batch \
  --rules-dir ./sigma-rules-repository \
  --workers 32 \
  --output ./comprehensive-tests \
  --pattern "**/*.yml" \
  --exclude "**/deprecated/**" \
  --exclude "**/experimental/**"
```

**Memory-Conscious Processing**:
```bash
# For systems with limited memory, reduce workers
sigsynth batch \
  --rules-dir ./large-ruleset \
  --workers 4 \
  --output ./tests
```

**Incremental Processing**:
```bash
# Process only changed rules (useful for CI/CD)
git diff --name-only HEAD~1 | grep '\.yml$' | while read rule; do
  sigsynth generate --rule "$rule" --output "./tests/$(dirname "$rule")"
done
```

## Best Practices

### Rule Organization

Organize your Sigma rules for efficient processing:

```
sigma-rules/
├── production/          # Stable, tested rules
│   ├── aws/
│   ├── windows/
│   └── linux/
├── development/         # Rules under development
├── experimental/        # Experimental rules (excluded by default)
└── deprecated/          # Old rules (excluded by default)
```

### Test Generation Strategy

**Development Phase**:
- Use fewer samples for faster iteration
- Enable debug mode for troubleshooting
- Test individual rules frequently
- Use consistent naming conventions

**Production Phase**:
- Generate comprehensive test suites
- Use consistent random seeds for reproducibility
- Validate all tests before deployment
- Archive test results for compliance

### Performance Guidelines

**Worker Count**:
- **I/O bound** (most cases): 2x CPU cores
- **CPU intensive rules**: 1x CPU cores  
- **Rate limited APIs**: 2-4 workers max

**Memory Usage**:
- ~10MB per worker + ~1MB per 100 test cases
- Monitor memory usage with large rule sets
- Use batch processing for 1000+ rules

**API Cost Management**:
- Use configuration files to standardize sample counts
- Set `SIGSYNTH_SAMPLES` environment variable for cost control
- Monitor OpenAI API usage in your dashboard
- Consider using cheaper models for development

### Quality Assurance

1. **Validate Generated Tests**:
   ```bash
   # Check test manifest for expected counts
   cat tests/panther/*/test_manifest.json | jq '.test_count'
   
   # Verify positive/negative test ratios
   cat tests/panther/*/test_manifest.json | jq '{positive: .positive_tests, negative: .negative_tests}'
   ```

2. **Review Sample Test Cases**:
   ```bash
   # Examine generated test cases
   cat tests/panther/rule-name/test_000.json | jq .
   
   # Check for realistic data
   cat tests/panther/rule-name/test_*.json | jq -r '.log.eventName' | sort | uniq -c
   ```

3. **Platform Compatibility**:
   ```bash
   # Check for compatibility warnings in output
   sigsynth batch --rules-dir ./rules --output ./tests 2>&1 | grep -i "warning"
   ```

## Troubleshooting

### Common Issues

#### "OpenAI API key not provided"
**Cause**: Missing or incorrect API key  
**Solution**: 
```bash
export OPENAI_API_KEY="your-actual-api-key"
# Verify it's set:
echo $OPENAI_API_KEY
```

#### "No rule files found matching criteria"
**Cause**: Incorrect patterns or paths  
**Solution**:
```bash
# Check if files exist
ls -la your-rules-directory/
# Try broader patterns
sigsynth batch --rules-dir ./rules --pattern "**/*" --output ./tests
```

#### "Rate limit exceeded"
**Cause**: Too many API requests  
**Solution**:
```bash
# Reduce workers
sigsynth batch --workers 2 --rules-dir ./rules --output ./tests
# Or add delays between requests
SIGSYNTH_PARALLEL_WORKERS=1 sigsynth batch --rules-dir ./rules --output ./tests
```

#### Memory issues with large rule sets
**Cause**: Processing too many rules simultaneously  
**Solution**:
```bash
# Process in smaller batches
sigsynth batch --rules-dir ./rules/batch1 --output ./tests/batch1
sigsynth batch --rules-dir ./rules/batch2 --output ./tests/batch2
# Or reduce workers
sigsynth batch --workers 2 --rules-dir ./rules --output ./tests
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Environment variable
SIGSYNTH_DEBUG=true sigsynth generate --rule rule.yml --output ./tests

# Configuration file
debug:
  enabled: true
  verbose: true
  trace_validation: true
```

### Performance Issues

**Slow API responses**:
```bash
# Reduce parallel requests
sigsynth batch --workers 2 --rules-dir ./rules --output ./tests
```

**High memory usage**:
```bash
# Monitor memory usage
top -p $(pgrep -f sigsynth)
# Reduce sample count
SIGSYNTH_SAMPLES=100 sigsynth batch --rules-dir ./rules --output ./tests
```

## Performance Optimization

### Benchmarks

| Rule Count | Workers | Time | API Calls | Cost (est.) |
|------------|---------|------|-----------|-------------|
| 1 rule | 1 | 10s | 1 | $0.01-0.05 |
| 10 rules | 4 | 30s | 10 | $0.10-0.50 |
| 100 rules | 8 | 5min | 100 | $1-5 |
| 1000 rules | 16 | 45min | 1000 | $10-50 |

*Performance varies based on rule complexity, API response times, and hardware.*

### Optimization Tips

1. **Use configuration files** to avoid re-specifying options
2. **Set appropriate worker counts** based on your CPU and API limits
3. **Use patterns and exclusions** to process only relevant rules
4. **Enable fail-fast in CI/CD** to catch issues early
5. **Monitor API usage** to manage costs
6. **Cache results** when possible for repeated runs

### Hardware Recommendations

**Development Machine**:
- 4+ CPU cores
- 8GB+ RAM
- SSD storage
- Stable internet connection

**Production/CI Server**:
- 8+ CPU cores
- 16GB+ RAM
- Fast SSD storage
- High-bandwidth internet

## Platform-Specific Guides

### Panther

**Output Structure**:
```
tests/panther/
├── rule-name-1/
│   ├── test_000.json
│   ├── test_001.json
│   └── test_manifest.json
└── rule-name-2/
    ├── test_000.json
    └── test_manifest.json
```

**Integration with Panther Rules SDK**:
```bash
# Generate tests
sigsynth batch --rules-dir ./panther-rules --output ./tests

# Use with Panther CLI
panther test --path ./tests/panther/
```

**Panther-Specific Configuration**:
```yaml
platforms:
  panther:
    name: panther
    output_format: json
    custom_options:
      test_prefix: "test_"
      include_metadata: true
      panther_version: "1.x"
```

### Splunk (Coming Soon)

**Expected Output Structure**:
```
tests/splunk/
├── rule-name-1.spl
├── rule-name-2.spl
└── test_manifest.json
```

**Planned Features**:
- SPL query generation
- Splunk field mappings
- Index pattern optimization
- Time range specifications

## Getting Help

- **GitHub Issues**: Report bugs and feature requests at https://github.com/haasonsaas/sigsynth/issues
- **Discussions**: Ask questions and share use cases
- **Documentation**: Check the main README and this usage guide

```bash
# Get help for any command
sigsynth --help
sigsynth generate --help
sigsynth batch --help
```

---

**Happy testing! 🚀**

For more information, visit: https://github.com/haasonsaas/sigsynth