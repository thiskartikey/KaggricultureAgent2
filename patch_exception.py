with open("revancedmain.py", "r") as f:
    code = f.read()
code = code.replace("except Exception:\n        return", "except Exception as e:\n        import traceback; traceback.print_exc(); return")
with open("revancedmain.py", "w") as f:
    f.write(code)
