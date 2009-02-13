if not hasattr(context, 'isAlphaFlowable'):
    return False

if not context.isAlphaFlowable():
    return False

if not context.hasInstanceAssigned():
    return False

try:
  instance = context.getInstance()
except:
  return False

return instance.state == "failed"
