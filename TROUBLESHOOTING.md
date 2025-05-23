# SigSynth Troubleshooting Guide

Quick solutions for common issues when using SigSynth.

## Common Error Messages

### "OpenAI API key not provided"

**Problem**: Missing or invalid OpenAI API key

**Solutions**:
```bash
# Set the API key environment variable
export OPENAI_API_KEY="your-actual-api-key-here"

# Verify it's set correctly
echo $OPENAI_API_KEY

# For Windows:
set OPENAI_API_KEY=your-actual-api-key-here
```

### "No rule files found matching criteria"

**Problem**: SigSynth can't find your rule files

**Solutions**:
```bash
# Check if files exist in the directory
ls -la ./your-rules-directory/

# Try with broader patterns
sigsynth batch --rules-dir ./rules --pattern "**/*" --output ./tests

# Check current directory
sigsynth batch --rules-dir . --pattern "*.yml" --output ./tests

# Use absolute paths
sigsynth batch --rules-dir /full/path/to/rules --output ./tests
```

### "Rate limit exceeded" / "Too many requests"

**Problem**: Making too many API calls too quickly

**Solutions**:
```bash
# Reduce number of parallel workers
sigsynth batch --workers 2 --rules-dir ./rules --output ./tests

# Process rules one at a time
sigsynth batch --workers 1 --rules-dir ./rules --output ./tests

# Use environment variable
SIGSYNTH_PARALLEL_WORKERS=1 sigsynth batch --rules-dir ./rules --output ./tests
```

### "Invalid Sigma rule file" / Validation errors

**Problem**: Rule file is missing required fields

**Common fixes**:
```yaml
# Ensure your rule has all required fields:
title: Your Rule Title           # Required
id: your-rule-id                # Required
description: Rule description    # Required
status: test                    # Required
author: Your Name              # Required
date: 2024/01/01              # Required
logsource:                    # Required
  product: aws
  service: cloudtrail
level: medium                 # Required
tags:                        # Required
  - attack.initial_access
detection:                   # Required
  selection:
    eventName: CreateTrail
  condition: selection
```

### Memory issues / System slowdown

**Problem**: Using too much memory with large rule sets

**Solutions**:
```bash
# Reduce parallel workers
sigsynth batch --workers 2 --rules-dir ./rules --output ./tests

# Process smaller batches
sigsynth batch --rules-dir ./rules/batch1 --output ./tests/batch1
sigsynth batch --rules-dir ./rules/batch2 --output ./tests/batch2

# Reduce sample count
SIGSYNTH_SAMPLES=100 sigsynth batch --rules-dir ./rules --output ./tests
```

## Performance Issues

### Slow processing

**Causes & Solutions**:

1. **Too many workers for your system**:
   ```bash
   # Use fewer workers (rule of thumb: 1-2x CPU cores)
   sigsynth batch --workers 4 --rules-dir ./rules --output ./tests
   ```

2. **Network latency to OpenAI API**:
   ```bash
   # Reduce parallel requests
   sigsynth batch --workers 2 --rules-dir ./rules --output ./tests
   ```

3. **Complex rules taking longer**:
   ```bash
   # Reduce sample count for development
   sigsynth generate --rule complex_rule.yml --samples 50 --output ./tests
   ```

### High API costs

**Cost reduction strategies**:

```bash
# Use fewer seed samples
sigsynth batch --seed-samples 3 --rules-dir ./rules --output ./tests

# Generate fewer total samples
sigsynth batch --samples 100 --rules-dir ./rules --output ./tests

# Use configuration to set defaults
echo "seed_samples: 3\nsamples: 100" > dev.yaml
sigsynth --config dev.yaml batch --rules-dir ./rules --output ./tests
```

## Debug Mode

Enable debug mode to see detailed information:

```bash
# Environment variable
SIGSYNTH_DEBUG=true sigsynth generate --rule rule.yml --output ./tests

# Configuration file
debug:
  enabled: true
  verbose: true
  trace_validation: true
```

## File and Directory Issues

### Permission errors

```bash
# Make sure you have write permissions
chmod 755 ./output-directory

# Use absolute paths
sigsynth batch --rules-dir /full/path/to/rules --output /full/path/to/output
```

### "File not found" errors

```bash
# Check file paths
ls -la ./path/to/rule.yml

# Use absolute paths
sigsynth generate --rule /full/path/to/rule.yml --output ./tests

# Check current directory
pwd
ls -la
```

## Platform-Specific Issues

### Panther compatibility warnings

These are informational and don't stop processing:

```
Fields may need Panther mapping: customField1, customField2
Logsource aws/custom may require custom Panther log schema
```

**Solutions**:
- Review generated tests to ensure they match your log format
- Consider creating custom field mappings for your environment
- Check Panther documentation for supported log sources

## Getting More Help

### Enable verbose logging

```bash
# See detailed processing information
SIGSYNTH_DEBUG=true SIGSYNTH_DEBUG_VERBOSE=true sigsynth generate --rule rule.yml --output ./tests
```

### Check specific test output

```bash
# Look at generated test manifest
cat ./tests/panther/rule-name/test_manifest.json

# Examine individual test cases
cat ./tests/panther/rule-name/test_000.json | jq .

# Check test counts
find ./tests -name "test_manifest.json" -exec jq '.test_count' {} \;
```

### System information

```bash
# Check Python version
python3 --version

# Check available memory
free -h  # Linux
vm_stat  # macOS

# Check CPU cores
nproc    # Linux
sysctl -n hw.ncpu  # macOS
```

## When to Contact Support

If you've tried the above solutions and still have issues:

1. **Gather information**:
   ```bash
   # Run with debug mode
   SIGSYNTH_DEBUG=true sigsynth your-command 2>&1 | tee debug.log
   
   # Check system resources
   top -n 1
   ```

2. **Create a minimal example**:
   - Use a single, simple rule file
   - Use default settings
   - Note exact error messages

3. **Report the issue**:
   - [GitHub Issues](https://github.com/haasonsaas/sigsynth/issues)
   - Include debug output, system info, and minimal example
   - Describe what you expected vs. what happened

## Quick Fixes Checklist

- [ ] OpenAI API key is set correctly
- [ ] Rule files exist and are valid YAML
- [ ] Output directory is writable
- [ ] Not hitting API rate limits (reduce workers)
- [ ] Enough memory available (reduce workers/samples)
- [ ] Network connection is stable
- [ ] Using supported Python version (3.8+)

---

**Still need help?** Check the [full usage guide](./USAGE.md) or [open an issue](https://github.com/haasonsaas/sigsynth/issues).