"""
Zero-Cost Filesystem Security for Local-Only Agent Access.

This module implements RED-aligned security with:
- LOCAL-FIRST: Filesystem-based access controls with no external dependencies
- COST-FIRST: $0 security infrastructure using local filesystem permissions
- SIMPLE-SCALE: Right-sized for 5 users with minimal overhead
- AGENT-NATIVE: Security controls accessible through MCP interfaces
"""

import os
import pwd
import grp
import stat
import logging
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LocalAccessPolicy:
    """Local filesystem access policy for agents."""
    policy_id: str
    agent_id: str
    allowed_paths: List[str]
    denied_paths: List[str]
    allowed_operations: List[str]  # read, write, execute, list
    max_file_size_mb: int = 10
    allowed_extensions: List[str] = None
    created_timestamp: float = None

    def __post_init__(self):
        if self.created_timestamp is None:
            self.created_timestamp = time.time()
        if self.allowed_extensions is None:
            self.allowed_extensions = [".txt", ".json", ".md", ".py", ".mojo"]


@dataclass
class SecurityAuditEntry:
    """Security audit log entry."""
    timestamp: float
    agent_id: str
    operation: str
    path: str
    result: str  # "allowed", "denied", "error"
    reason: str
    user_context: str


class ZeroCostLocalSecurity:
    """
    Zero-cost filesystem security manager for agent access control.

    Implements RED principles:
    - LOCAL-FIRST: Filesystem-based security with no external services
    - COST-FIRST: No security infrastructure costs
    - SIMPLE-SCALE: Optimized for 5 users
    - AGENT-NATIVE: MCP-accessible security validation
    """

    def __init__(self, config_dir: str = "/home/junior/src/red/agent-system/config"):
        """Initialize zero-cost local security system."""
        self.config_dir = Path(config_dir)
        self.security_dir = self.config_dir / "security"
        self.security_dir.mkdir(parents=True, exist_ok=True)

        self.policies: Dict[str, LocalAccessPolicy] = {}
        self.audit_log: List[SecurityAuditEntry] = []

        # Define safe base paths for agent operations
        self.safe_base_paths = {
            "/home/junior/src/red/uploads",
            "/home/junior/src/red/web_rag_data",
            "/home/junior/src/red/agent-system/config",
            "/home/junior/src/red/chromadb_data"
        }

        # Define forbidden paths (system critical)
        self.forbidden_paths = {
            "/etc",
            "/usr/bin",
            "/usr/sbin",
            "/bin",
            "/sbin",
            "/root",
            "/home/junior/.ssh",
            "/home/junior/.aws",
            "/home/junior/.docker"
        }

        # Load existing policies
        self._load_security_policies()

        # Set up default policies
        self._initialize_default_policies()

        logger.info("Zero-Cost Local Security Manager initialized")

    def _load_security_policies(self):
        """Load security policies from local filesystem."""
        policy_files = list(self.security_dir.glob("policy_*.json"))

        for policy_file in policy_files:
            try:
                with open(policy_file, 'r') as f:
                    policy_data = json.load(f)

                policy = LocalAccessPolicy(**policy_data)
                self.policies[policy.policy_id] = policy

                logger.info(f"Loaded security policy: {policy.policy_id}")

            except Exception as e:
                logger.error(f"Failed to load policy {policy_file}: {e}")

    def _initialize_default_policies(self):
        """Initialize default security policies for RED-aligned agents."""

        # Default policy for RAG research agents
        rag_policy = LocalAccessPolicy(
            policy_id="rag_research_agent_policy",
            agent_id="*_research_*",  # Pattern matching
            allowed_paths=[
                "/home/junior/src/red/uploads",
                "/home/junior/src/red/web_rag_data",
                "/home/junior/src/red/chromadb_data"
            ],
            denied_paths=[
                "/home/junior/.ssh",
                "/home/junior/.aws",
                "/etc"
            ],
            allowed_operations=["read", "list"],
            max_file_size_mb=50,
            allowed_extensions=[".txt", ".pdf", ".doc", ".docx", ".md", ".csv", ".xls", ".xlsx"]
        )

        # Default policy for code review agents
        code_review_policy = LocalAccessPolicy(
            policy_id="code_review_agent_policy",
            agent_id="*_code_*",  # Pattern matching
            allowed_paths=[
                "/home/junior/src/red",
                "/home/junior/src/red/agent-system",
                "/home/junior/src/red/rag-system",
                "/home/junior/src/red/multi-index-system"
            ],
            denied_paths=[
                "/home/junior/src/red/.venv",
                "/home/junior/.ssh",
                "/home/junior/.aws"
            ],
            allowed_operations=["read", "list"],
            max_file_size_mb=5,
            allowed_extensions=[".py", ".mojo", ".js", ".ts", ".json", ".md", ".txt"]
        )

        # Default policy for vector analysis agents
        vector_analysis_policy = LocalAccessPolicy(
            policy_id="vector_analysis_agent_policy",
            agent_id="*_vector_*",  # Pattern matching
            allowed_paths=[
                "/home/junior/src/red/chromadb_data",
                "/home/junior/src/red/agent-system/config"
            ],
            denied_paths=[],
            allowed_operations=["read", "list"],
            max_file_size_mb=100,
            allowed_extensions=[".db", ".json", ".parquet", ".arrow"]
        )

        # Store default policies
        default_policies = [rag_policy, code_review_policy, vector_analysis_policy]

        for policy in default_policies:
            if policy.policy_id not in self.policies:
                self.register_policy(policy)

        logger.info(f"Initialized {len(default_policies)} default security policies")

    def register_policy(self, policy: LocalAccessPolicy) -> bool:
        """Register a new security policy."""
        try:
            # Validate policy
            if not self._validate_policy(policy):
                logger.error(f"Policy validation failed: {policy.policy_id}")
                return False

            # Store policy
            self.policies[policy.policy_id] = policy

            # Save to filesystem
            policy_file = self.security_dir / f"policy_{policy.policy_id}.json"
            with open(policy_file, 'w') as f:
                json.dump(asdict(policy), f, indent=2)

            logger.info(f"Registered security policy: {policy.policy_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register policy {policy.policy_id}: {e}")
            return False

    def validate_access(self, agent_id: str, operation: str, path: str) -> Dict[str, Any]:
        """
        Validate agent access to filesystem path with comprehensive checking.

        Returns detailed validation result for MCP interface consumption.
        """
        result = {
            "allowed": False,
            "reason": "",
            "policy_applied": None,
            "security_level": "denied",
            "timestamp": time.time()
        }

        try:
            # Find applicable policy
            applicable_policy = self._find_applicable_policy(agent_id)
            if not applicable_policy:
                result["reason"] = "No applicable security policy found"
                self._audit_access(agent_id, operation, path, "denied", result["reason"])
                return result

            result["policy_applied"] = applicable_policy.policy_id

            # Check operation permission
            if operation not in applicable_policy.allowed_operations:
                result["reason"] = f"Operation '{operation}' not allowed by policy"
                self._audit_access(agent_id, operation, path, "denied", result["reason"])
                return result

            # Normalize and validate path
            normalized_path = os.path.abspath(path)

            # Check forbidden paths
            if self._is_forbidden_path(normalized_path):
                result["reason"] = f"Path '{normalized_path}' is in forbidden system directories"
                self._audit_access(agent_id, operation, path, "denied", result["reason"])
                return result

            # Check allowed paths
            if not self._is_allowed_path(normalized_path, applicable_policy.allowed_paths):
                result["reason"] = f"Path '{normalized_path}' not in allowed paths"
                self._audit_access(agent_id, operation, path, "denied", result["reason"])
                return result

            # Check denied paths
            if self._is_denied_path(normalized_path, applicable_policy.denied_paths):
                result["reason"] = f"Path '{normalized_path}' is explicitly denied"
                self._audit_access(agent_id, operation, path, "denied", result["reason"])
                return result

            # Check file extension if applicable
            if os.path.isfile(normalized_path):
                file_ext = Path(normalized_path).suffix.lower()
                if file_ext and file_ext not in applicable_policy.allowed_extensions:
                    result["reason"] = f"File extension '{file_ext}' not allowed"
                    self._audit_access(agent_id, operation, path, "denied", result["reason"])
                    return result

                # Check file size
                try:
                    file_size_mb = os.path.getsize(normalized_path) / (1024 * 1024)
                    if file_size_mb > applicable_policy.max_file_size_mb:
                        result["reason"] = f"File size {file_size_mb:.1f}MB exceeds limit {applicable_policy.max_file_size_mb}MB"
                        self._audit_access(agent_id, operation, path, "denied", result["reason"])
                        return result
                except FileNotFoundError:
                    # File doesn't exist yet - allow for write operations
                    pass

            # Check filesystem permissions
            if not self._check_filesystem_permissions(normalized_path, operation):
                result["reason"] = f"Insufficient filesystem permissions for '{operation}' on '{normalized_path}'"
                self._audit_access(agent_id, operation, path, "denied", result["reason"])
                return result

            # All checks passed
            result["allowed"] = True
            result["security_level"] = "allowed"
            result["reason"] = "Access granted by security policy"

            self._audit_access(agent_id, operation, path, "allowed", result["reason"])

            return result

        except Exception as e:
            result["reason"] = f"Security validation error: {str(e)}"
            self._audit_access(agent_id, operation, path, "error", result["reason"])
            logger.error(f"Security validation failed: {e}")
            return result

    def _find_applicable_policy(self, agent_id: str) -> Optional[LocalAccessPolicy]:
        """Find the most specific applicable policy for an agent."""
        applicable_policies = []

        for policy in self.policies.values():
            if self._agent_matches_policy(agent_id, policy.agent_id):
                applicable_policies.append(policy)

        if not applicable_policies:
            return None

        # Return most specific policy (exact match preferred over patterns)
        exact_matches = [p for p in applicable_policies if p.agent_id == agent_id]
        if exact_matches:
            return exact_matches[0]

        # Return first pattern match
        return applicable_policies[0]

    def _agent_matches_policy(self, agent_id: str, policy_pattern: str) -> bool:
        """Check if agent ID matches policy pattern."""
        if policy_pattern == agent_id:
            return True

        # Simple wildcard matching
        if "*" in policy_pattern:
            import fnmatch
            return fnmatch.fnmatch(agent_id, policy_pattern)

        return False

    def _is_forbidden_path(self, path: str) -> bool:
        """Check if path is in forbidden system directories."""
        path = os.path.abspath(path)

        for forbidden in self.forbidden_paths:
            if path.startswith(forbidden):
                return True

        return False

    def _is_allowed_path(self, path: str, allowed_paths: List[str]) -> bool:
        """Check if path is within allowed directories."""
        path = os.path.abspath(path)

        for allowed in allowed_paths:
            allowed_abs = os.path.abspath(allowed)
            if path.startswith(allowed_abs):
                return True

        return False

    def _is_denied_path(self, path: str, denied_paths: List[str]) -> bool:
        """Check if path is explicitly denied."""
        path = os.path.abspath(path)

        for denied in denied_paths:
            denied_abs = os.path.abspath(denied)
            if path.startswith(denied_abs):
                return True

        return False

    def _check_filesystem_permissions(self, path: str, operation: str) -> bool:
        """Check actual filesystem permissions."""
        try:
            # Get current user info
            current_uid = os.getuid()
            current_gid = os.getgid()

            # For non-existent files, check parent directory
            check_path = path
            if not os.path.exists(path):
                check_path = os.path.dirname(path)

            if not os.path.exists(check_path):
                return False

            # Get file stats
            file_stat = os.stat(check_path)

            # Check ownership and permissions
            file_mode = file_stat.st_mode

            # Owner permissions
            if file_stat.st_uid == current_uid:
                if operation == "read" and not (file_mode & stat.S_IRUSR):
                    return False
                if operation == "write" and not (file_mode & stat.S_IWUSR):
                    return False
                if operation == "execute" and not (file_mode & stat.S_IXUSR):
                    return False

            # Group permissions (simplified check)
            elif file_stat.st_gid == current_gid:
                if operation == "read" and not (file_mode & stat.S_IRGRP):
                    return False
                if operation == "write" and not (file_mode & stat.S_IWGRP):
                    return False
                if operation == "execute" and not (file_mode & stat.S_IXGRP):
                    return False

            # Other permissions
            else:
                if operation == "read" and not (file_mode & stat.S_IROTH):
                    return False
                if operation == "write" and not (file_mode & stat.S_IWOTH):
                    return False
                if operation == "execute" and not (file_mode & stat.S_IXOTH):
                    return False

            return True

        except Exception as e:
            logger.error(f"Filesystem permission check failed: {e}")
            return False

    def _validate_policy(self, policy: LocalAccessPolicy) -> bool:
        """Validate security policy for RED compliance."""
        try:
            # Check that allowed paths are within safe base paths
            for allowed_path in policy.allowed_paths:
                abs_allowed = os.path.abspath(allowed_path)
                is_safe = any(abs_allowed.startswith(safe) for safe in self.safe_base_paths)

                if not is_safe:
                    logger.error(f"Policy validation failed: '{allowed_path}' not in safe paths")
                    return False

            # Check file size limits (5-user optimization)
            if policy.max_file_size_mb > 100:
                logger.error(f"Policy validation failed: File size limit {policy.max_file_size_mb}MB exceeds RED limits")
                return False

            return True

        except Exception as e:
            logger.error(f"Policy validation failed: {e}")
            return False

    def _audit_access(self, agent_id: str, operation: str, path: str, result: str, reason: str):
        """Log access attempt for audit trail."""
        try:
            audit_entry = SecurityAuditEntry(
                timestamp=time.time(),
                agent_id=agent_id,
                operation=operation,
                path=path,
                result=result,
                reason=reason,
                user_context=f"uid:{os.getuid()}"
            )

            self.audit_log.append(audit_entry)

            # Keep audit log size manageable (5-user optimization)
            if len(self.audit_log) > 1000:
                self.audit_log = self.audit_log[-500:]  # Keep last 500 entries

            # Write to audit file for persistence
            audit_file = self.security_dir / "access_audit.jsonl"
            with open(audit_file, 'a') as f:
                f.write(json.dumps(asdict(audit_entry)) + "\n")

        except Exception as e:
            logger.error(f"Audit logging failed: {e}")

    def get_audit_log(self, agent_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries for MCP interface consumption."""
        filtered_log = self.audit_log

        if agent_id:
            filtered_log = [entry for entry in filtered_log if entry.agent_id == agent_id]

        # Return most recent entries
        recent_entries = filtered_log[-limit:] if len(filtered_log) > limit else filtered_log

        return [asdict(entry) for entry in recent_entries]

    def get_security_status(self) -> Dict[str, Any]:
        """Get overall security system status for monitoring."""
        return {
            "total_policies": len(self.policies),
            "audit_entries": len(self.audit_log),
            "safe_base_paths": list(self.safe_base_paths),
            "forbidden_paths": list(self.forbidden_paths),
            "security_mode": "local_filesystem",
            "cost": "$0 (filesystem-based)",
            "red_compliant": True
        }

    def create_secure_workspace(self, agent_id: str) -> str:
        """Create a secure workspace directory for an agent."""
        try:
            # Create agent-specific workspace
            workspace_dir = Path(f"/home/junior/src/red/agent-system/workspaces/{agent_id}")
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # Set appropriate permissions (user read/write only)
            os.chmod(workspace_dir, 0o700)

            logger.info(f"Created secure workspace for {agent_id}: {workspace_dir}")
            return str(workspace_dir)

        except Exception as e:
            logger.error(f"Failed to create secure workspace for {agent_id}: {e}")
            raise


if __name__ == "__main__":
    # Initialize security system
    security = ZeroCostLocalSecurity()

    # Test access validation
    test_cases = [
        ("rag_research_assistant", "read", "/home/junior/src/red/uploads/test.txt"),
        ("code_review_agent", "read", "/home/junior/src/red/app.js"),
        ("malicious_agent", "read", "/etc/passwd"),
        ("vector_analyst", "read", "/home/junior/src/red/chromadb_data/index.db")
    ]

    for agent_id, operation, path in test_cases:
        result = security.validate_access(agent_id, operation, path)
        print(f"Agent: {agent_id}, Operation: {operation}, Path: {path}")
        print(f"  Result: {'ALLOWED' if result['allowed'] else 'DENIED'}")
        print(f"  Reason: {result['reason']}")
        print()