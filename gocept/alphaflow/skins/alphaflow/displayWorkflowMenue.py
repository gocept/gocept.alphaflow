##parameters=member

a = hasattr(context, 'isAlphaFlowable') and context.isAlphaFlowable()
b = member.has_permission('Work with process instance', context)
c = 'portal_factory' not in context.REQUEST.URL0


if a and b and c:
    return True

return False
