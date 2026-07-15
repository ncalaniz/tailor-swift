# check_setup.py — confirms the workshop is ready.
import sys
import anthropic

print("Python version:", sys.version.split()[0])
print("anthropic package:", anthropic.__version__)
print("Setup is solid. Ready for Stage 2.")