import sys

# Disable unhandled exceptions
if hasattr(sys, "unraisablehook"):
    sys.unraisablehook = lambda *args: None
