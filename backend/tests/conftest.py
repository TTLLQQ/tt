import os
import tempfile

_temp = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{_temp.name}/test.db"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-that-is-long-enough-123456"
os.environ["DATA_ENCRYPTION_KEY"] = "test-data-encryption-secret-1234567890"
os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "test-admin"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "test-password-long"
