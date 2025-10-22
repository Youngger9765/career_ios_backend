"""Tests for base schemas"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.base import BaseResponse, BaseSchema


class TestBaseSchema:
    """Test BaseSchema configuration"""

    def test_base_schema_from_attributes_enabled(self):
        """Test that from_attributes=True allows ORM model conversion"""

        # Mock ORM object with attributes
        class MockORMObject:
            name = "test_name"
            value = 42

        # BaseSchema should be able to convert from ORM attributes
        class TestSchema(BaseSchema):
            name: str
            value: int

        # This should work with from_attributes=True
        obj = MockORMObject()
        schema = TestSchema.model_validate(obj)

        assert schema.name == "test_name"
        assert schema.value == 42

    def test_base_schema_inheritance(self):
        """Test that child schemas inherit from_attributes config"""

        class ChildSchema(BaseSchema):
            field1: str
            field2: int

        # Mock ORM object
        class MockORM:
            field1 = "value1"
            field2 = 100

        obj = MockORM()
        schema = ChildSchema.model_validate(obj)

        assert schema.field1 == "value1"
        assert schema.field2 == 100


class TestBaseResponse:
    """Test BaseResponse schema"""

    def test_base_response_required_fields(self):
        """Test that BaseResponse requires id and created_at"""
        test_id = uuid4()
        test_time = datetime.now()

        response = BaseResponse(
            id=test_id, created_at=test_time, updated_at=None
        )

        assert response.id == test_id
        assert response.created_at == test_time
        assert response.updated_at is None

    def test_base_response_with_updated_at(self):
        """Test BaseResponse with updated_at value"""
        test_id = uuid4()
        created_time = datetime.now()
        updated_time = datetime.now()

        response = BaseResponse(
            id=test_id, created_at=created_time, updated_at=updated_time
        )

        assert response.id == test_id
        assert response.created_at == created_time
        assert response.updated_at == updated_time

    def test_base_response_from_orm_object(self):
        """Test BaseResponse can be created from ORM object"""

        # Mock ORM object
        class MockModel:
            id = uuid4()
            created_at = datetime.now()
            updated_at = None

        obj = MockModel()
        response = BaseResponse.model_validate(obj)

        assert response.id == obj.id
        assert response.created_at == obj.created_at
        assert response.updated_at is None

    def test_base_response_missing_required_fields(self):
        """Test that BaseResponse raises error for missing fields"""
        with pytest.raises(ValidationError) as exc_info:
            BaseResponse(id=uuid4())  # Missing created_at

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("created_at",) for err in errors)
