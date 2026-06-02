"""
Tests for the Mergington High School Activities API.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test."""
    from src.app import activities
    # Store original state
    original = {
        key: {
            **value,
            "participants": value["participants"].copy()
        }
        for key, value in activities.items()
    }
    yield
    # Restore original state after test
    for key in activities:
        activities[key]["participants"] = original[key]["participants"].copy()


class TestRootEndpoint:
    """Tests for the GET / endpoint."""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to /static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivitiesEndpoint:
    """Tests for the GET /activities endpoint."""

    def test_get_activities_success(self, client, reset_activities):
        """Test that GET /activities returns all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify activity structure
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_get_activities_contains_participants(self, client, reset_activities):
        """Test that activities include their participants."""
        response = client.get("/activities")
        data = response.json()
        
        # Verify participants are present
        chess_club = data["Chess Club"]
        assert len(chess_club["participants"]) > 0
        assert "michael@mergington.edu" in chess_club["participants"]


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity."""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_to_participants(self, client, reset_activities):
        """Test that signup actually adds the participant."""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]

    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup with non-existent activity."""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_duplicate_email(self, client, reset_activities):
        """Test signup with duplicate email for same activity."""
        email = "michael@mergington.edu"
        response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_same_email_different_activity(self, client, reset_activities):
        """Test that same email can signup for different activities."""
        email = "newstudent@mergington.edu"
        
        # Sign up for first activity
        response1 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Sign up for second activity
        response2 = client.post(
            f"/activities/Programming Class/signup?email={email}"
        )
        assert response2.status_code == 200

    def test_signup_with_special_characters_in_activity_name(self, client, reset_activities):
        """Test signup with activity name that needs URL encoding."""
        # The app should handle activity names properly
        email = "newstudent@mergington.edu"
        response = client.post(
            "/activities/Science%20Olympiad/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipantEndpoint:
    """Tests for the DELETE /activities/{activity_name}/participants endpoint."""

    def test_remove_participant_success(self, client, reset_activities):
        """Test successful removal of a participant."""
        email = "michael@mergington.edu"
        response = client.delete(
            f"/activities/Chess Club/participants?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert email in data["message"]
        assert "Removed" in data["message"]

    def test_remove_participant_actually_removes(self, client, reset_activities):
        """Test that remove actually removes the participant."""
        email = "michael@mergington.edu"
        
        # Verify participant exists
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
        
        # Remove participant
        client.delete(f"/activities/Chess Club/participants?email={email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        assert email not in response.json()["Chess Club"]["participants"]

    def test_remove_participant_activity_not_found(self, client, reset_activities):
        """Test remove participant with non-existent activity."""
        response = client.delete(
            "/activities/Nonexistent Activity/participants?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_remove_participant_not_in_activity(self, client, reset_activities):
        """Test remove participant that doesn't exist in activity."""
        response = client.delete(
            "/activities/Chess Club/participants?email=notasignup@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Participant not found" in data["detail"]

    def test_remove_then_signup_again(self, client, reset_activities):
        """Test that a participant can sign up again after being removed."""
        email = "michael@mergington.edu"
        
        # Remove participant
        client.delete(f"/activities/Chess Club/participants?email={email}")
        
        # Sign up again
        response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify they were added back
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
