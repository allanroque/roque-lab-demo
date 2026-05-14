# Tests for aap.security.restrict_sensitive_credentials
#
# Run with:
#   opa test aap_policy_examples/ test_aap_policy_examples/ -v
package aap.security.restrict_sensitive_credentials_test

import data.aap.security.restrict_sensitive_credentials
import rego.v1

# ------------------------------------------------------------------------------
# ALLOW: sensitive credential + approved repo + approved branch -> allowed
# ------------------------------------------------------------------------------
test_allow_machine_credential_from_approved_repo if {
	result := restrict_sensitive_credentials.allowed with input as {
		"credentials": [{"name": "linux-prod", "kind": "ssh"}],
		"project": {
			"scm_url": "https://git.example.com/automation/prod-playbooks.git",
			"scm_branch": "main",
		},
		"job_template": {"name": "linux_patching"},
	}
	result == true
}

# ------------------------------------------------------------------------------
# ALLOW: no sensitive credential at all -> allowed
# (a vanilla read-only job from any repo is not gated by this policy)
# ------------------------------------------------------------------------------
test_allow_when_no_sensitive_credential if {
	result := restrict_sensitive_credentials.allowed with input as {
		"credentials": [{"name": "satellite-readonly", "kind": "satellite6"}],
		"project": {
			"scm_url": "https://git.example.com/sandbox/playground.git",
			"scm_branch": "feature-x",
		},
		"job_template": {"name": "inventory_sync"},
	}
	result == true
}

# ------------------------------------------------------------------------------
# DENY: the actual incident — sensitive cred from an unapproved sandbox repo
# ------------------------------------------------------------------------------
test_deny_sensitive_credential_from_sandbox_repo if {
	result := restrict_sensitive_credentials.allowed with input as {
		"credentials": [
			{"name": "linux-prod", "kind": "ssh"},
			{"name": "aws-prod", "kind": "aws"},
		],
		"project": {
			"scm_url": "https://git.example.com/sandbox/debug-lab.git",
			"scm_branch": "main",
		},
		"job_template": {"name": "linux_debug_variables_lab"},
	}
	result == false
}

# ------------------------------------------------------------------------------
# DENY: approved repo but wrong branch
# ------------------------------------------------------------------------------
test_deny_when_branch_not_approved if {
	violations := restrict_sensitive_credentials.violations with input as {
		"credentials": [{"name": "linux-prod", "kind": "ssh"}],
		"project": {
			"scm_url": "https://git.example.com/automation/prod-playbooks.git",
			"scm_branch": "developer-personal-branch",
		},
		"job_template": {"name": "linux_patching"},
	}
	count(violations) > 0
}

# ------------------------------------------------------------------------------
# DENY: AWS credential, missing project metadata entirely
# ------------------------------------------------------------------------------
test_deny_when_project_metadata_missing if {
	result := restrict_sensitive_credentials.allowed with input as {
		"credentials": [{"name": "aws-prod", "kind": "aws"}],
		"project": {},
		"job_template": {"name": "aws_inspect"},
	}
	result == false
}

# ------------------------------------------------------------------------------
# Alternative AAP input shape: credential_type.kind (some versions)
# ------------------------------------------------------------------------------
test_deny_using_credential_type_kind_shape if {
	result := restrict_sensitive_credentials.allowed with input as {
		"credentials": [{
			"name": "vault-prod",
			"credential_type": {"kind": "vault"},
		}],
		"project": {
			"scm_url": "https://git.example.com/sandbox/playground.git",
			"scm_branch": "main",
		},
		"job_template": {"name": "vault_extract"},
	}
	result == false
}