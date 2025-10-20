from backend.core.rbac import Principal, Role


def test_org_admin_privileges():
    principal = Principal(subject="1", org_roles={1: Role.ORG_ADMIN})
    assert principal.can_manage_organization(1) is True
    assert principal.can_manage_billing(1) is True
    assert principal.can_manage_task(owner_user_id=2, organization_id=1, assigned_team_id=None) is True
    assert principal.can_manage_organization(2) is False


def test_team_manager_privileges():
    principal = Principal(subject="2", team_roles={3: Role.TEAM_MANAGER})
    assert principal.can_manage_team(3, organization_id=None) is True
    assert principal.can_manage_assignments(organization_id=None, team_id=3) is True
    assert principal.can_manage_task(owner_user_id=5, organization_id=None, assigned_team_id=3) is True
    assert principal.can_manage_organization(1) is False


def test_member_self_management():
    principal = Principal(subject="10", org_roles={5: Role.MEMBER})
    assert principal.can_manage_task(owner_user_id=10, organization_id=5, assigned_team_id=None) is True
    assert principal.can_manage_task(owner_user_id=11, organization_id=5, assigned_team_id=None) is False


def test_system_admin_overrides():
    principal = Principal(subject="99", global_roles={Role.SYSTEM_ADMIN})
    assert principal.can_manage_organization(123) is True
    assert principal.can_manage_task(owner_user_id=None, organization_id=None, assigned_team_id=None) is True
