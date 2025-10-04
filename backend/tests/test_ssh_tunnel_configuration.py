import os

import pytest

from thoth_core.admin_models.admin_sqldb import SqlDbAdminForm
from thoth_core.dbmanagement import _build_ssh_connection_params
from thoth_core.models import SQLDBChoices, SSHAuthMethod, SqlDb


@pytest.mark.django_db
def test_sqldb_admin_form_requires_ssh_host_when_enabled():
    form = SqlDbAdminForm(
        data={
            "name": "Test SSH DB",
            "db_type": SQLDBChoices.POSTGRES,
            "db_name": "test_db",
            "db_mode": "dev",
            "ssh_enabled": True,
            "ssh_username": "bastion_user",
            "ssh_port": 22,
            "ssh_auth_method": SSHAuthMethod.PASSWORD,
            "ssh_password": "secret",
        }
    )

    assert not form.is_valid()
    assert "ssh_host" in form.errors


@pytest.mark.django_db
def test_build_ssh_connection_params_success(tmp_path):
    key_path = tmp_path / "id_rsa"
    key_path.write_text("fake-key")

    sqldb = SqlDb(
        name="SSH Enabled",
        db_type=SQLDBChoices.POSTGRES,
        db_name="db",
        db_host="remote-db",
        db_port=5432,
        user_name="db_user",
        ssh_enabled=True,
        ssh_host="bastion.example.com",
        ssh_port=2222,
        ssh_username="bastion_user",
        ssh_auth_method=SSHAuthMethod.PRIVATE_KEY,
        ssh_private_key_path=str(key_path),
        ssh_strict_host_key_check=True,
    )

    params = _build_ssh_connection_params(sqldb)

    assert params["ssh_enabled"] is True
    assert params["ssh_host"] == "bastion.example.com"
    assert params["ssh_port"] == 2222
    assert params["ssh_username"] == "bastion_user"
    assert params["ssh_private_key_path"] == str(key_path)
    assert params["ssh_auth_method"] == SSHAuthMethod.PRIVATE_KEY


@pytest.mark.django_db
def test_build_ssh_connection_params_missing_values():
    sqldb = SqlDb(
        name="SSH Missing",
        db_type=SQLDBChoices.POSTGRES,
        db_name="db",
        db_host="remote-db",
        db_port=None,
        ssh_enabled=True,
        ssh_host="",
        ssh_username="",
    )

    with pytest.raises(ValueError):
        _build_ssh_connection_params(sqldb)
