def is_admin(user):
    return getattr(getattr(user, "role", None), "role", "") == "admin" or user.is_staff

def is_trainer(user):
    return getattr(getattr(user, "role", None), "role", "") == "trainer"