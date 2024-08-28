import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import CarMake, CarModel
from .populate import initiate
from .restapis import (
    get_request,
    analyze_review_sentiments,
    post_review
)

# Get an instance of a logger
logger = logging.getLogger(__name__)


@csrf_exempt
def login_user(request):
    """Handle sign-in requests."""
    data = json.loads(request.body)
    username = data.get('userName')
    password = data.get('password')
    user = authenticate(username=username, password=password)
    response_data = {"userName": username}

    if user is not None:
        login(request, user)
        response_data["status"] = "Authenticated"

    return JsonResponse(response_data)


def logout_request(request):
    """Handle sign-out requests."""
    logout(request)
    return JsonResponse({"userName": ""})


@csrf_exempt
def registration(request):
    """Handle sign-up requests."""
    data = json.loads(request.body)
    username = data.get('userName')
    password = data.get('password')
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    email = data.get('email')
    username_exist = User.objects.filter(username=username).exists()

    if not username_exist:
        User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            email=email
        )
        login(
            request,
            authenticate(username=username, password=password)
        )
        return JsonResponse({
            "userName": username,
            "status": "Authenticated"
        })
    else:
        return JsonResponse({
            "userName": username,
            "error": "Already Registered"
        })


def get_cars(request):
    """Get the list of cars."""
    count = CarMake.objects.count()
    if count == 0:
        initiate()

    car_models = CarModel.objects.select_related('car_make')
    cars = [
        {"CarModel": car_model.name,
         "CarMake": car_model.car_make.name}
        for car_model in car_models
    ]
    return JsonResponse({"CarModels": cars})


def get_dealerships(request, state="All"):
    """Render a list of dealerships; all by default,
    or particular state if passed."""
    endpoint = "/fetchDealers" if state == "All" else f"/fetchDealers/{state}"
    dealerships = get_request(endpoint)
    return JsonResponse({
        "status": 200,
        "dealers": dealerships
    })


def get_dealer_reviews(request, dealer_id):
    """Render the reviews of a dealer."""
    if dealer_id:
        endpoint = f"/fetchReviews/dealer/{dealer_id}"
        reviews = get_request(endpoint)
        for review_detail in reviews:
            response = analyze_review_sentiments(
                review_detail['review']
            )
            review_detail['sentiment'] = response['sentiment']
        return JsonResponse({
            "status": 200,
            "reviews": reviews
        })
    return JsonResponse({
        "status": 400,
        "message": "Bad Request"
    })


def get_dealer_details(request, dealer_id):
    """Render the details of a dealer."""
    if dealer_id:
        endpoint = f"/fetchDealer/{dealer_id}"
        dealership = get_request(endpoint)
        return JsonResponse({
            "status": 200,
            "dealer": dealership
        })
    return JsonResponse({
        "status": 400,
        "message": "Bad Request"
    })


def add_review(request):
    """Submit a review."""
    if not request.user.is_anonymous:
        data = json.loads(request.body)
        try:
            post_review(data)
            return JsonResponse({"status": 200})
        except Exception:
            return JsonResponse({
                "status": 401,
                "message": "Error in posting review"
            })
        finally:
            print("add_review request successful!")
    return JsonResponse({
        "status": 403,
        "message": "Unauthorized"
    })
