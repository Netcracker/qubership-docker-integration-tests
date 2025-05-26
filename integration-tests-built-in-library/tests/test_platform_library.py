import pytest
from unittest.mock import Mock, patch
from kubernetes import client
from integration_library_builtIn.PlatformLibrary import PlatformLibrary

@pytest.fixture
def mock_k8s_client():
    with patch('kubernetes.client') as mock_client:
        # Mock CoreV1Api
        mock_core_v1 = Mock()
        mock_client.CoreV1Api.return_value = mock_core_v1
        
        # Mock AppsV1Api
        mock_apps_v1 = Mock()
        mock_client.AppsV1Api.return_value = mock_apps_v1
        
        # Mock CustomObjectsApi
        mock_custom_objects = Mock()
        mock_client.CustomObjectsApi.return_value = mock_custom_objects
        
        # Mock NetworkingV1Api
        mock_networking = Mock()
        mock_client.NetworkingV1Api.return_value = mock_networking
        
        yield mock_client

@pytest.fixture
def platform_library(mock_k8s_client):
    return PlatformLibrary(managed_by_operator="true")

def test_get_deployment_entity(platform_library, mock_k8s_client):
    # Arrange
    mock_deployment = Mock()
    mock_deployment.metadata.name = "test-deployment"
    mock_deployment.spec.replicas = 3
    platform_library.k8s_apps_v1_client.read_namespaced_deployment.return_value = mock_deployment

    # Act
    result = platform_library.get_deployment_entity("test-deployment", "test-namespace")

    # Assert
    assert result.metadata.name == "test-deployment"
    assert result.spec.replicas == 3
    platform_library.k8s_apps_v1_client.read_namespaced_deployment.assert_called_once_with(
        "test-deployment", "test-namespace"
    )

def test_get_service(platform_library, mock_k8s_client):
    # Arrange
    mock_service = Mock()
    mock_service.metadata.name = "test-service"
    mock_service.spec.selector = {"app": "test"}
    platform_library.k8s_core_v1_client.read_namespaced_service.return_value = mock_service

    # Act
    result = platform_library.get_service("test-service", "test-namespace")

    # Assert
    assert result.metadata.name == "test-service"
    assert result.spec.selector == {"app": "test"}
    platform_library.k8s_core_v1_client.read_namespaced_service.assert_called_once_with(
        "test-service", "test-namespace"
    )

def test_get_pods(platform_library, mock_k8s_client):
    # Arrange
    mock_pod1 = Mock()
    mock_pod1.metadata.name = "pod-1"
    mock_pod2 = Mock()
    mock_pod2.metadata.name = "pod-2"
    platform_library.k8s_core_v1_client.list_namespaced_pod.return_value.items = [mock_pod1, mock_pod2]

    # Act
    result = platform_library.get_pods("test-namespace")

    # Assert
    assert len(result) == 2
    assert result[0].metadata.name == "pod-1"
    assert result[1].metadata.name == "pod-2"
    platform_library.k8s_core_v1_client.list_namespaced_pod.assert_called_once_with("test-namespace")

def test_get_route(platform_library, mock_k8s_client):
    # Arrange
    mock_route = {
        "spec": {
            "host": "test-route.example.com"
        }
    }
    platform_library.custom_objects_api.get_namespaced_custom_object.return_value = mock_route

    # Act
    result = platform_library.get_route("test-route", "test-namespace")

    # Assert
    assert result["spec"]["host"] == "test-route.example.com"
    platform_library.custom_objects_api.get_namespaced_custom_object.assert_called_once_with(
        group="route.openshift.io",
        version="v1",
        namespace="test-namespace",
        plural="routes",
        name="test-route"
    )

def test_get_route_url(platform_library, mock_k8s_client):
    # Arrange
    mock_route = {
        "spec": {
            "host": "test-route.example.com"
        }
    }
    platform_library.custom_objects_api.get_namespaced_custom_object.return_value = mock_route

    # Act
    result = platform_library.get_route_url("test-route", "test-namespace")

    # Assert
    assert result == "http://test-route.example.com"

def test_scale_up_deployment_entity(platform_library, mock_k8s_client):
    # Arrange
    mock_scale = Mock()
    mock_scale.spec.replicas = 2
    mock_scale.status.replicas = 2
    platform_library.k8s_apps_v1_client.read_namespaced_deployment_scale.return_value = mock_scale

    # Act
    platform_library.scale_up_deployment_entity("test-deployment", "test-namespace")

    # Assert
    assert mock_scale.spec.replicas == 3
    assert mock_scale.status.replicas == 3
    platform_library.k8s_apps_v1_client.patch_namespaced_deployment_scale.assert_called_once()

def test_scale_down_deployment_entity(platform_library, mock_k8s_client):
    # Arrange
    mock_scale = Mock()
    mock_scale.spec.replicas = 2
    mock_scale.status.replicas = 2
    platform_library.k8s_apps_v1_client.read_namespaced_deployment_scale.return_value = mock_scale

    # Act
    platform_library.scale_down_deployment_entity("test-deployment", "test-namespace")

    # Assert
    assert mock_scale.spec.replicas == 1
    assert mock_scale.status.replicas == 1
    platform_library.k8s_apps_v1_client.patch_namespaced_deployment_scale.assert_called_once()

def test_get_config_map(platform_library, mock_k8s_client):
    # Arrange
    mock_config_map = Mock()
    mock_config_map.metadata.name = "test-config"
    mock_config_map.data = {"key": "value"}
    platform_library.k8s_core_v1_client.read_namespaced_config_map.return_value = mock_config_map

    # Act
    result = platform_library.get_config_map("test-config", "test-namespace")

    # Assert
    assert result.metadata.name == "test-config"
    assert result.data == {"key": "value"}
    platform_library.k8s_core_v1_client.read_namespaced_config_map.assert_called_once_with(
        "test-config", "test-namespace"
    )

def test_get_secret(platform_library, mock_k8s_client):
    # Arrange
    mock_secret = Mock()
    mock_secret.metadata.name = "test-secret"
    mock_secret.data = {"key": "dmFsdWU="}  # base64 encoded "value"
    platform_library.k8s_core_v1_client.read_namespaced_secret.return_value = mock_secret

    # Act
    result = platform_library.get_secret("test-secret", "test-namespace")

    # Assert
    assert result.metadata.name == "test-secret"
    assert result.data == {"key": "dmFsdWU="}
    platform_library.k8s_core_v1_client.read_namespaced_secret.assert_called_once_with(
        "test-secret", "test-namespace"
    ) 