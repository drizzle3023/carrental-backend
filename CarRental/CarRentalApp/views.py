from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser

from django.utils.timezone import make_aware
from copy import deepcopy
from django.db.models import Q, Count

from .models import User
from .models import Company
from .models import Coverage
from .models import Payment
from .models import History
from .models import CarType
from .models import Claim
from .models import Support
from .models import FileUploadTest

# For parsing request from android app
from .app_serializers import SignUpSerializer
from .app_serializers import SignInSerializer
from .app_serializers import SignVerifySerializer
from .app_serializers import AddCoverageSerializer
from .app_serializers import AddClaimSerializer
from .app_serializers import AddPaymentSerializer

# For managing db
from .serializers import UserEntrySerializer
from .serializers import FileUploadTestSerializer

import json
import requests
import Adyen
import logging
import ast
import geopy.distance
import pytz
import datetime
import os
from urllib.parse import unquote

from .constants import url_authentication_server, application_id, adyen_api_key, currency_usd, currency_eur
from .utils import func_generate_user_app_id, func_generate_claim_id

##########################################################################   Login APIs   #######################################################################

# SignUp #
class SignUpView(APIView):

    def post(self, request):

        signup_serializer = SignUpSerializer(data=request.data)
        if (signup_serializer.is_valid()):

            # Receive mobile, name from app
            mobile = signup_serializer.data.get("mobile")
            email = signup_serializer.data.get("email")
            name = signup_serializer.data.get("name")
            car_type_id = signup_serializer.data.get("car_type_id")
            world_zone = signup_serializer.data.get("world_zone")

            if mobile == None:
                message = "required_mobile"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)
            if email == None:
                message = "required_email"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)
            if name == None:
                message = "required_name"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)
            # if car_type_id == None:
            #     message = "required_car_type"
            #     response_data = {"success": "false", "data": {"message": message}}
            #     return Response(response_data, status=status.HTTP_200_OK)
            # if world_zone == None:
            #     message = "required_world_zone"
            #     response_data = {"success": "false", "data": {"message": message}}
            #     return Response(response_data, status=status.HTTP_200_OK)

            # Check if there's the mobile number alreday in DB.
            existed_user = User.objects.filter(mobile = mobile).first()
            if existed_user != None:
                if existed_user.access_token != None:
                    response_data = {"success": "false", "data": {"message": "The mobile is already registered."}}
                    return Response(response_data, status=status.HTTP_200_OK)

            # Send request signin to the SDK server
            request_data = signup_serializer.data
            # Global Constants -> this url. ?? https://api.platform.integrations.muzzley.com/
            # Application ID -> 6eb9d03d-33da-4bcc-9722-611bb9c9fec2
            url_to_send = url_authentication_server + '/v3/applications/' + application_id + '/user-sms-entry'
            response = requests.post(url_to_send, data = request_data)
            jsonResponse = json.loads(response.content)

            # Check if jsonResponse has success value.
            if status.is_success(response.status_code) == False:
                if jsonResponse.get("code") == 21211:
                    message = "invalid_mobile"
                else:
                    message = "Authentication server error"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)

            if existed_user != None:
                existed_user.user_id = jsonResponse.get("id")
                existed_user.name = name
                existed_user.mobile = jsonResponse.get("mobile")
                existed_user.namespace = jsonResponse.get("namespace")
                existed_user.confirmation_hash = jsonResponse.get("confirmation_hash")
                existed_user.target_id = jsonResponse.get("target_id")
                existed_user.href = jsonResponse.get("href")
                existed_user.type = jsonResponse.get("type")
                existed_user.created_at = jsonResponse.get("created")
                existed_user.updated_at = jsonResponse.get("updated")
                existed_user.email = email
                existed_user.car_type_id = car_type_id
                existed_user.world_zone = world_zone
                existed_user.save()

                response_data = {"success": "true", "data": {"message": "Sign up succeeded."}}
                return Response(response_data, status = status.HTTP_200_OK)
            else:

                temp_user_app_id = func_generate_user_app_id()

                user_app_id = {'user_app_id': temp_user_app_id}
                email_object = {'email': email}
                car_type_id_object = {'car_type_id': car_type_id}
                world_zone_object = {'world_zone': world_zone}

                jsonResponse.update(email_object)
                jsonResponse.update(car_type_id_object)
                jsonResponse.update(world_zone_object)
                jsonResponse.update(user_app_id)

                user_entry_serializer = UserEntrySerializer(data = jsonResponse)

                if user_entry_serializer.is_valid():
                    user_entry_serializer.create(jsonResponse)
                    response_data = {"success": "true", "data": {"message": "Sign up succeeded."}}
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "There's a problem with saving your information."}}
                    return Response(response_data, status=status.HTTP_200_OK)

        response_data = {"success": "false", "data":{"message": "There's a problem with receiving your information."}}
        return Response(response_data, status=status.HTTP_200_OK)

# SignIn #
class SignInView(APIView):

    def post(self, request):
        signin_serializer = SignInSerializer(data=request.data)
        if (signin_serializer.is_valid()):

            # Receive mobile, name from app
            mobile = signin_serializer.data.get("mobile")

            if mobile == None:
                message = "required_mobile"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)

            user = User.objects.filter(mobile = mobile).first()

            if user == None:
                response_data = {"success": "false", "data": {"message": "The mobile isn't registered."}}
                return Response(response_data, status=status.HTTP_200_OK)

            # Send request signin to the SDK server
            request_data = signin_serializer.data
            # Global Constants -> this url. ??
            url_to_send = url_authentication_server + '/v3/applications/' + application_id + '/user-sms-entry'
            response = requests.post(url_to_send, data = request_data)
            try:
                jsonResponse = json.loads(response.content)
            except:
                message = "authentication server error"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)

            # Check if jsonResponse has success value.
            if status.is_success(response.status_code) == False:
                if jsonResponse.get("code") == 21211:
                    message = "invalid_mobile"
                else:
                    message = "authentication server error"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)

            # Check if there's the mobile number alreday in DB.
            existed_user = User.objects.filter(mobile = mobile).first()

            if existed_user != None:
                existed_user.user_id = jsonResponse.get("id")
                existed_user.name = jsonResponse.get("name")
                existed_user.mobile = jsonResponse.get("mobile")
                existed_user.namespace = jsonResponse.get("namespace")
                existed_user.confirmation_hash = jsonResponse.get("confirmation_hash")
                existed_user.target_id = jsonResponse.get("target_id")
                existed_user.href = jsonResponse.get("href")
                existed_user.type = jsonResponse.get("type")
                existed_user.created_at = jsonResponse.get("created")
                existed_user.updated_at = jsonResponse.get("updated")
                existed_user.save()
                response_data = {"success": "true", "data": {"message": "Login request succeeded."}}
                return Response(response_data, status = status.HTTP_200_OK)
            else:
                response_data = {"success": "false", "data": {"message": "Your phone number isn't registered."}}
                return Response(response_data, status=status.HTTP_200_OK)

        response_data = {"success": "false", "data":{"message": "There's a problem with receiving your information."}}
        return Response(response_data, status=status.HTTP_200_OK)

# Sign Verify #
class SignVerifyView(APIView):

    def post(self, request):
        signverify_serializer = SignVerifySerializer(data = request.data)
        if (signverify_serializer.is_valid()):
            mobile = signverify_serializer.data.get("mobile")
            code = signverify_serializer.data.get("code")

            if mobile == None:
                message = "required_mobile"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)

            if code == None:
                message = "required_code"
                response_data = {"success": "false", "data": {"message": message}}
                return Response(response_data, status=status.HTTP_200_OK)

            # Check if there's the mobile number alreday in DB.
            existed_user = User.objects.filter(mobile = mobile).first()

            if existed_user != None:
                user_id = existed_user.user_id
                confirmation_hash = existed_user.confirmation_hash
                request_data = {'confirmation_hash': confirmation_hash, 'code': code}
                headers = {'Content-Type': 'application/json'}
                # request_verify_serializer = RequestVerifySerializer()
                # request_verify_serializer.confirmation_hash = confirmation_hash
                # request_verify_serializer.code = code

                url_to_send = url_authentication_server + '/v3/users/' + user_id + '/sms-verify'

                response = requests.post(url_to_send, data = json.dumps(request_data), headers = headers)

                if status.is_success(response.status_code) == False:

                    jsonResponse = json.loads(response.content)
                    response_data = {"success": "false", "data": {"message": "Verification failed."}}
                    return Response(response_data, status = status.HTTP_200_OK)
                else:

                    if response.status_code == status.HTTP_200_OK:

                        jsonResponse = json.loads(response.content)
                        # Parse endpoints, scope
                        endpoints = jsonResponse.get("endpoints")
                        scope = jsonResponse.get("scope")

                        existed_user.access_token = jsonResponse.get("access_token")
                        existed_user.client_id = jsonResponse.get("client_id")
                        existed_user.code = jsonResponse.get("code")
                        existed_user.expires_at = jsonResponse.get("expires")
                        existed_user.grant_type = jsonResponse.get("grant_type")
                        existed_user.href = jsonResponse.get("href")
                        existed_user.owner_id = jsonResponse.get("owner_id")
                        existed_user.refresh_token = jsonResponse.get("refresh_token")
                        existed_user.endpoints_http = endpoints.get("http")
                        existed_user.endpoints_mqtt = endpoints.get("mqtt")
                        existed_user.endpoints_uploader = endpoints.get("uploader")
                        existed_user.scope_1 = scope[0]
                        existed_user.scope_2 = scope[1]
                        existed_user.created_at = jsonResponse.get("created")
                        existed_user.updated_at = jsonResponse.get("updated")

                        existed_user.save()

                        carTypeInfo = CarType.objects.filter(id=existed_user.car_type_id).first()

                        if carTypeInfo != None:
                            response_carType = {
                                "id": carTypeInfo.id,
                                "name": carTypeInfo.name,
                                "icon_url": str(carTypeInfo.icon_url),
                                "price_per_year_usd": carTypeInfo.price_per_year_usd,
                                "price_per_year_eur": carTypeInfo.price_per_year_eur
                            }
                        else:
                            response_carType = None

                        response_userProfile = {
                            "id": existed_user.id,
                            "email": existed_user.email,
                            "name": existed_user.name,
                            "mobile": existed_user.mobile,
                            "car_type": response_carType,
                            "world_zone": existed_user.world_zone,
                            "pay_state": existed_user.pay_state
                        }

                        response_data = {"success": "true", "data": {
                            "message": "Sms verification succeeded.",
                            "access_token": jsonResponse.get("access_token"),
                            "user": jsonResponse,
                            "user_profile": response_userProfile}}
                        return Response(response_data, status = status.HTTP_200_OK)
                    else:
                        response_data = {"success": "false", "data": {
                            "message": "Content error from server."}}
                        return Response(response_data, status = status.HTTP_200_OK)
            else:
                response_data = {"success": "false", "data": {"message": "Your phone number isn't registered."}}
                return Response(response_data, status=status.HTTP_200_OK)

# Check access_token validation
def checkAccessToken(access_token):

    existed_user = User.objects.filter(access_token = access_token).first()

    if existed_user != None:

        expires_at = existed_user.expires_at
        current_datatime = datetime.datetime.now()

        if expires_at != None:

            timestamp_expires_at = expires_at.timestamp()
            timestamp_current_datetime = current_datatime.timestamp()

            if timestamp_current_datetime > timestamp_expires_at:

                # Send the request with refresh_token
                host = existed_user.endpoints_http
                refresh_token = existed_user.refresh_token
                url = host + '/v3/auth/exchange?client_id=6eb9d03d-33da-4bcc-9722-611bb9c9fec2&refresh_token=' + refresh_token + '&grant_type=password'
                response = requests.get(url, timeout = 10)
                jsonResponse = json.loads(response.content)

                if status.is_success(response.status_code) == False:

                    token_state = {"state": "invalid"}
                    return token_state
                else:
                    # Sending refresh_token succeeded.
                    if response.status_code == status.HTTP_200_OK:

                        endpoints = jsonResponse.get("endpoints")
                        scope = jsonResponse.get("scope")

                        existed_user.access_token = jsonResponse.get("access_token")
                        existed_user.client_id = jsonResponse.get("client_id")
                        existed_user.code = jsonResponse.get("code")
                        existed_user.endpoints_http = endpoints.get("http")
                        existed_user.endpoints_mqtt = endpoints.get("mqtt")
                        existed_user.endpoints_uploader = endpoints.get("uploader")
                        existed_user.expires_at = jsonResponse.get("expires")
                        existed_user.grant_type = jsonResponse.get("grant_type")
                        existed_user.href = jsonResponse.get("href")
                        existed_user.owner_id = jsonResponse.get("owner_id")
                        existed_user.refresh_token = jsonResponse.get("refresh_token")
                        existed_user.scope_1 = scope[0]
                        existed_user.scope_2 = scope[1]
                        existed_user.created_at = jsonResponse.get("created")
                        existed_user.updated_at = jsonResponse.get("updated")

                        existed_user.save()

                        # Send request for access_token validation
                        host = existed_user.endpoints_http
                        owner_id = existed_user.owner_id

                        url = host + '/v3/users/' + owner_id
                        authorization = 'Bearer ' + existed_user.access_token
                        header = {'Authorization': authorization}
                        response = requests.get(url, headers=header)

                        if status.is_success(response.status_code) == False:

                            token_state = {"state": "invalid"}
                            return token_state
                        else:
                            # Receiving response data succeeded.
                            if response.status_code == status.HTTP_200_OK:

                                token_state = {"state": "valid", "user_id": existed_user.id, "refresh_user": jsonResponse}
                                return token_state

                            else:
                                token_state = {"state": "invalid"}
                                return token_state
                    else:
                        token_state = {"state": "invalid"}
                        return token_state
            else:
                # Send the request for checking access_token
                host = existed_user.endpoints_http
                owner_id = existed_user.owner_id

                url = host + '/v3/users/' + owner_id
                authorization = 'Bearer ' + access_token
                header = {'Authorization': authorization}
                response = requests.get(url, headers = header)
                #jsonResponse = json.loads(response.content)

                if status.is_success(response.status_code) == False:

                    token_state = {"state": "invalid"}
                    return token_state
                else:
                    # Receiving response data succeeded.
                    if response.status_code == status.HTTP_200_OK:

                        token_state = {"state": "valid", "user_id": existed_user.id}
                        return token_state
                    else:
                        token_state = {"state": "invalid"}
                        return token_state

        else:
            token_state = {"state": "invalid"}
            return token_state

    else:
        token_state = {"state": "invalid"}
        return token_state

# Get payment methods #
class GetPaymentMethodsView(APIView):

    def post(self, request):

        access_token = request.data.get("access_token")
        car_type_id = request.data.get("car_type_id")
        world_zone = request.data.get("world_zone")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    car_type = CarType.objects.filter(id = car_type_id).first()

                    if car_type == None:

                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false",
                                             "data": {"message": "The car type doesn't exist.",
                                                      "refresh_user": resultCheckingResult.get("refresh_user"),
                                                      "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)
                        else:
                            response_data = {"success": "false",
                                             "data": {"message": "The car type doesn't exist.",
                                                      "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)

                    userInfo.car_type_id = car_type_id
                    userInfo.world_zone = world_zone
                    userInfo.save()

                    if world_zone == 'EU':
                        amount = car_type.price_per_year_eur
                        currency = currency_eur
                    else:
                        amount = car_type.price_per_year_usd
                        currency = currency_usd

                    request_data = deepcopy(request.data)
                    request_data['user_id'] = userInfo.id
                    request_data['amount'] = amount
                    request_data['currency'] = currency
                    request_data['state'] = 1

                    adyen = Adyen.Adyen(
                        app_name = "CarRental",
                        xapikey = adyen_api_key,
                        platform = "test"
                    )

                    result = adyen.checkout.payment_methods({
                        'merchantAccount': 'HabitAccount235ECOM',
                        'channel': 'Android'
                    })

                    if result.status_code == 200:

                        add_payment_serializer = AddPaymentSerializer(data=request_data)
                        if (add_payment_serializer.is_valid()):

                            obj = add_payment_serializer.save();

                            if resultCheckingResult.get("refresh_user") != None:

                                response_data = {"success": "true", "data": {
                                    "message": "Getting payment methods succeeded.",
                                    "paymentMethods": result.message,
                                    "payment_id": obj.id,
                                    "refresh_user": resultCheckingResult.get("refresh_user"),
                                    "token_state": "valid"}}
                            else:
                                response_data = {"success": "true", "data": {
                                    "message": "Getting payment methods succeeded.",
                                    "paymentMethods": result.message,
                                    "payment_id": obj.id,
                                    "token_state": "valid"}}

                            return Response(response_data, status=status.HTTP_200_OK)
                        else:
                            response_data = {"success": "false", "data": {
                                "message": add_payment_serializer.errors,
                                "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        response_data = {"success": "false", "data": {
                            "message": "Getting payment methods failed.",
                            "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)

                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Pay #
class PaymentView(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")
        payment_id = request.data.get("payment_id")
        payment_component_data = request.data.get("paymentComponentData")

        payment_method = payment_component_data.get("paymentMethod")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    payment = Payment.objects.filter(id = payment_id).first()

                    if payment != None:

                        adyen = Adyen.Adyen(
                            app_name="CarRental",
                            xapikey=adyen_api_key,
                            platform="test"
                        )

                        reference = "car_rental_payment" + str(payment_id)

                        try:
                            result = adyen.checkout.payments({
                                'amount':{
                                    'value': payment.amount * 100,
                                    'currency': payment.currency
                                },
                                'reference': reference,
                                'paymentMethod': payment_method,
                                'merchantAccount': 'HabitAccount235ECOM',
                                'channel': 'Android',
                                'returnUrl': 'https://your-company.com/checkout?shopperOrder=12xy'
                            })
                        except:
                            if resultCheckingResult.get("refresh_user") != None:
                                response_data = {"success": "false", "data": {
                                    "message": "Payment failed.",
                                    "token_state": "valid",
                                    "refresh_user": resultCheckingResult.get("refresh_user")}}
                                return Response(response_data, status=status.HTTP_200_OK)
                            else:
                                response_data = {"success": "false", "data": {
                                    "message": "Payment failed.",
                                    "token_state": "valid"}}
                                return Response(response_data, status=status.HTTP_200_OK)

                        if result.status_code == 200:

                            if 'action' in result.message:

                                payment = Payment.objects.filter(id = payment_id).first()
                                payment.state = 2
                                payment.save()

                                if resultCheckingResult.get("refresh_user") != None:
                                    response_data = {"success": "true", "data": {
                                        "action": result.message['action'],
                                        "message": "More action needed.",
                                        "refresh_user": resultCheckingResult.get("refresh_user"),
                                        "token_state": "valid"}}
                                else:
                                    response_data = {"success": "true", "data": {
                                        "action": result.message['action'],
                                        "message": "More action needed.",
                                        "token_state": "valid"}}
                            elif result.message['resultCode'] == 'Authorised' :

                                payment = Payment.objects.filter(id = payment_id).first()
                                payment.state = 7
                                payment.save()

                                userInfo.pay_state = 1
                                userInfo.save()

                                if resultCheckingResult.get("refresh_user") != None:
                                    response_data = {"success": "true", "data": {
                                        "message": "Payment succeeded.",
                                        "resultCode": result.message['resultCode'],
                                        "refresh_user": resultCheckingResult.get("refresh_user"),
                                        "token_state": "valid"}}
                                else:
                                    response_data = {"success": "true", "data": {
                                        "message": "Payment succeeded.",
                                        "resultCode": result.message['resultCode'],
                                        "token_state": "valid"}}

                            elif result.message['resultCode'] == 'Pending':

                                payment = Payment.objects.filter(id=payment_id).first()
                                payment.state = 6
                                payment.save()

                                if resultCheckingResult.get("refresh_user") != None:
                                    response_data = {"success": "true", "data": {
                                        "message": "Payment is pending.",
                                        "resultCode": result.message['resultCode'],
                                        "refresh_user": resultCheckingResult.get("refresh_user"),
                                        "token_state": "valid"}}
                                else:
                                    response_data = {"success": "true", "data": {
                                        "message": "Payment is pending.",
                                        "resultCode": result.message['resultCode'],
                                        "token_state": "valid"}}

                            elif result.message['resultCode'] == 'Received' :

                                payment = Payment.objects.filter(id = payment_id).first()
                                payment.state = 5
                                payment.save()

                                if resultCheckingResult.get("refresh_user") != None:
                                    response_data = {"success": "true", "data": {
                                        "message": "Received payment. Please wait...",
                                        "resultCode": result.message['resultCode'],
                                        "refresh_user": resultCheckingResult.get("refresh_user"),
                                        "token_state": "valid"}}
                                else:
                                    response_data = {"success": "true", "data": {
                                        "message": "Received payment, Please wait...",
                                        "resultCode": result.message['resultCode'],
                                        "token_state": "valid"}}
                            else :
                                if result.message['resultCode'] == 'Refused':
                                    payment = Payment.objects.filter(id = payment_id).first()
                                    payment.state = 4
                                    payment.save()
                                else:
                                    payment = Payment.objects.filter(id = payment_id).first()
                                    payment.state = 3
                                    payment.save()

                                if resultCheckingResult.get("refresh_token") != None:
                                    response_data = {"success": "false", "data": {
                                        "message": result.message['refusalReason'],
                                        "resultCode": result.message['resultCode'],
                                        "refresh_user": resultCheckingResult.get("refresh_token"),
                                        "token_state": "valid"}}
                                else:
                                    response_data = {"success": "false", "data": {
                                        "message": result.message['refusalReason'],
                                        "resultCode": result.message['resultCode'],
                                        "token_state": "valid"}}


                            logger = logging.getLogger(__name__)
                            logger.error(result.message['resultCode'])

                            history_content = {}

                            history_content['id'] = payment.id
                            history_content['user_id'] = payment.user_id
                            history_content['car_type_id'] = payment.car_type_id
                            history_content['amount'] = payment.amount
                            history_content['currency'] = payment.currency
                            history_content['state'] = payment.state

                            payment_date = payment.date

                            if payment_date is None:
                                payment_date_timestamp = payment_date
                            else:
                                payment_date_timestamp = payment_date.timestamp()

                            history_content['date'] = int(payment_date_timestamp)

                            history_json_content = json.dumps(history_content)

                            history_data = History(user_id = userInfo.id, type = "Payment", content = history_json_content)
                            history_data.save()

                            return Response(response_data, status=status.HTTP_200_OK)
                        else:
                            if resultCheckingResult.get("refresh_user") != None:
                                response_data = {"success": "false", "data": {
                                    "message": "Payment failed.",
                                    "refresh_user": result.get("refresh_user"),
                                    "token_state": "valid"}}
                            else:
                                response_data = {"success": "false", "data": {
                                    "message": "Payment failed.",
                                    "token_state": "valid"}}

                            return Response(response_data, status=status.HTTP_200_OK)

                    else:
                        response_data = {"success": "false", "data": {"message": "The payment information doesn't exist.", "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)

                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Get user profile
class GetUserProfileView(APIView):

    def post(self, request):

        supportInfo = Support.objects.first()

        if supportInfo == None:
            responseSupportInfo = None;
        else:
            responseSupportInfo = {"phone_number": supportInfo.phone_number}

        access_token = request.data.get("access_token")

        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    carTypeInfo = CarType.objects.filter(id = userInfo.car_type_id).first()

                    if carTypeInfo != None:
                        response_carType = {
                            "id": carTypeInfo.id,
                            "name": carTypeInfo.name,
                            "icon_url": str(carTypeInfo.icon_url),
                            "price_per_year_usd": carTypeInfo.price_per_year_usd,
                            "price_per_year_eur": carTypeInfo.price_per_year_eur
                        }
                    else:
                        response_carType = None

                    if resultCheckingResult.get("refresh_user") != None:
                        response_data = {"success": "true",
                                         "data": {
                                            "message": "Succeeded.",
                                            "profile": {
                                                "id": userInfo.id,
                                                "email": userInfo.email,
                                                "name": userInfo.name,
                                                "mobile": userInfo.mobile,
                                                "car_type": response_carType,
                                                "world_zone": userInfo.world_zone,
                                                "pay_state": userInfo.pay_state
                                            },
                                            "support_info": responseSupportInfo,
                                            "token_state": "valid",
                                            "refresh_user": resultCheckingResult.get("refresh_user")}}
                    else:
                        response_data = {"success": "true",
                                         "data": {
                                            "message": "Succeeded.",
                                            "profile": {
                                                "id": userInfo.id,
                                                "email": userInfo.email,
                                                "name": userInfo.name,
                                                "mobile": userInfo.mobile,
                                                "car_type": response_carType,
                                                "world_zone": userInfo.world_zone,
                                                "pay_state": userInfo.pay_state
                                            },
                                            "support_info": responseSupportInfo,
                                            "token_state": "valid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "support_info": responseSupportInfo, "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                                              "support_info": responseSupportInfo,
                                                              "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "support_info": responseSupportInfo, "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Add coverage
class AddCoverageView(APIView):

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")

        # path = default_storage.save('video-vehicle.mp4', ContentFile(videoOne.read()))
        # tmp_file = os.path.join(settings.MEDIA_ROOT, path)

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    start_at = request.data.get("start_at")
                    end_at = request.data.get("end_at")

                    files = request.FILES

                    try:
                        videoMile = files['video-mile']
                    except:
                        videoMile = None
                    try:
                        videoVehicle = files['video-vehicle']
                    except:
                        videoVehicle = None
                    try:
                        imageMile = files['image-mile']
                    except:
                        imageMile = None
                    try:
                        imageVehicle = files['image-vehicle']
                    except:
                        imageVehicle = None

                    # Add user_id to the request data to save as a model field
                    if start_at == None:
                        start_at_datetime = start_at
                    else:
                        start_at_datetime = datetime.datetime.utcfromtimestamp(int(start_at))
                        start_at_datetime = start_at_datetime.strftime("%Y-%m-%d %H:%M:%S")

                    if end_at == None:
                        end_at_datetime = end_at
                    else:
                        end_at_datetime = datetime.datetime.utcfromtimestamp(int(end_at))
                        end_at_datetime = end_at_datetime.strftime("%Y-%m-%d %H:%M:%S")

                    # request_data = deepcopy(request.data)
                    # request_data['user_id'] = existed_user.id
                    # request_data['start_at'] = start_at_datetime
                    # request_data['end_at'] = end_at_datetime

                    add_coverage_serializer = AddCoverageSerializer(data = request.data)
                    if (add_coverage_serializer.is_valid()):

                        active_coverage = Coverage.objects.filter(user_id = userInfo.id).filter(state = 2).first()

                        if active_coverage != None:

                            if resultCheckingResult.get("refresh_user") != None:

                                response_data = {"success": "false", "data": {
                                    "message": "The covered coverage exists.",
                                    "coverage_id": active_coverage.id,
                                    "token_state": "valid",
                                    "refresh_user": resultCheckingResult.get("refresh_user")}}
                            else:
                                response_data = {"success": "false", "data": {
                                    "message": "The covered coverage exists.",
                                    "coverage_id": active_coverage.id,
                                    "token_state": "valid"}}

                            return Response(response_data, status=status.HTTP_200_OK)
                        else:
                            active_coverage = Coverage.objects.filter(user_id=userInfo.id).filter(state=1).first()

                        if active_coverage != None:

                            if request.data.get("name") != None:
                                active_coverage.name = unquote(request.data.get("name"))
                            if request.data.get("latitude") != None:
                                active_coverage.latitude = request.data.get("latitude")
                            if request.data.get("longitude") != None:
                                active_coverage.longitude = request.data.get("longitude")
                            if request.data.get("address") != None:
                                active_coverage.address = unquote(request.data.get("address"))
                            if request.data.get("company_id") != None:
                                active_coverage.company_id = request.data.get("company_id")
                            if request.data.get("start_at") != None:
                                active_coverage.starting_at = start_at_datetime
                            if request.data.get("end_at") != None:
                                active_coverage.ending_at = end_at_datetime
                            if videoMile!= None:
                                active_coverage.video_mile = videoMile
                            elif request.data.get("video_mile") != None:
                                    active_coverage.video_mile = request.data.get("video_mile")
                            if videoVehicle != None:
                                active_coverage.video_vehicle = videoVehicle
                            elif request.data.get("video_vehicle") != None:
                                active_coverage.video_vehicle = request.data.get("video_vehicle")
                            if imageMile!= None:
                                active_coverage.image_mile = imageMile
                            elif request.data.get("image_mile") != None:
                                    active_coverage.image_mile = request.data.get("image_mile")
                            if imageVehicle != None:
                                active_coverage.image_vehicle = imageVehicle
                            elif request.data.get("image_vehicle") != None:
                                active_coverage.image_vehicle = request.data.get("image_vehicle")
                            if request.data.get("state") != None:
                                active_coverage.state = request.data.get("state")

                            active_coverage.save()
                        else :
                            obj = add_coverage_serializer.save()

                            active_coverage = Coverage.objects.filter(id = obj.id).first()

                            active_coverage.user_id = userInfo.id
                            active_coverage.starting_at = start_at_datetime
                            active_coverage.ending_at = end_at_datetime

                            if request.data.get("name") != None:
                                active_coverage.name = unquote(request.data.get("name"))
                            if request.data.get("address") != None:
                                active_coverage.address = unquote(request.data.get("address"))

                            active_coverage.save()

                        if (int(request.data.get("state")) != 1):
                            history_content = {}

                            history_content['id'] = active_coverage.id
                            history_content['name'] = active_coverage.name
                            history_content['user_id'] = active_coverage.user_id
                            history_content['latitude'] = active_coverage.latitude
                            history_content['longitude'] = active_coverage.longitude
                            history_content['address'] = active_coverage.address
                            history_content['company_id'] = active_coverage.company_id
                            if start_at != None:
                                history_content['start_at'] = int(start_at)
                            else:
                                history_content['start_at'] = None
                            if end_at != None:
                                history_content['end_at'] = int(end_at)
                            else:
                                history_content['end_at'] = None
                            history_content['video_mile'] = str(active_coverage.video_mile)
                            history_content['video_vehicle'] = str(active_coverage.video_vehicle)
                            history_content['image_mile'] = str(active_coverage.image_mile)
                            history_content['image_vehicle'] = str(active_coverage.image_vehicle)
                            history_content['state'] = active_coverage.state
                            history_content['claim_count'] = 0;

                            json_content = json.dumps(history_content)

                            history_data = History(user_id = userInfo.id, type = "Coverage", content = str(json_content))
                            history_data.save()

                        if resultCheckingResult.get("refresh_user") != None:

                            response_data = {"success": "true", "data": {
                                "message": "Adding coverage succeeded.",
                                "coverage_id": active_coverage.id,
                                "token_state": "valid",
                                "refresh_user": resultCheckingResult.get("refresh_user")}}
                        else:
                            response_data = {"success": "true", "data": {
                                "message": "Adding coverage succeeded.",
                                "coverage_id": active_coverage.id,
                                "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false", "data": {"message": add_coverage_serializer.errors, "token_state": "valid", "refresh_user": resultCheckingResult.get("refresh_user")}}
                            return Response(response_data, status=status.HTTP_200_OK)
                        else:
                            response_data = {"success": "false", "data": {"message": add_coverage_serializer.errors, "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Get company list
class GetCarTypeListView(APIView):

    def post(self, request):

        car_type_list = CarType.objects.all()

        response_car_type_list = []

        for car_type in car_type_list:

            car_type_id = car_type.id
            car_type_name = car_type.name
            car_type_icon_url = car_type.icon_url
            price_per_year_usd = car_type.price_per_year_usd
            price_per_year_eur = car_type.price_per_year_eur

            record = {"id": car_type_id, "name": car_type_name, "icon_url": str(car_type_icon_url), "price_per_year_usd": price_per_year_usd,  "price_per_year_eur": price_per_year_eur}
            response_car_type_list.append(record)

        response_data = {"success": "true", "data": {
            "message": "Getting car type list succeeded.",
            "carTypeList": response_car_type_list}}

        return Response(response_data, status=status.HTTP_200_OK)

# Get active coverage list
class GetActiveCoverageView(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    pay_state = userInfo.pay_state

                    coverage = Coverage.objects.filter(user_id = userInfo.id).exclude(state=3).order_by('-updated_at').first()

                    if coverage != None:

                        if coverage.state == 5:
                            if resultCheckingResult.get("refresh_user") != None:
                                response_data = {"success": "false", "data": {
                                    "message": "The active coverage doesn't exist.",
                                    "pay_state": pay_state,
                                    "token_state": "valid",
                                    "refresh_user": resultCheckingResult.get("refresh_user")}}
                            else:
                                response_data = {"success": "false", "data": {
                                    "message": "The active coverage doesn't exist.",
                                    "pay_state": pay_state,
                                    "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)

                        coverage_id = coverage.id
                        coverage_name = coverage.name
                        coverage_latitude = coverage.latitude
                        coverage_longitude = coverage.longitude
                        coverage_address = coverage.address
                        coverage_company_id = coverage.company_id
                        coverage_start_at = coverage.starting_at
                        coverage_end_at = coverage.ending_at
                        coverage_video_mile = coverage.video_mile
                        coverage_video_vehicle = coverage.video_vehicle
                        coverage_image_mile = coverage.image_mile
                        coverage_image_vehicle = coverage.image_vehicle

                        # Check if the coverage is expired. If then, update the state of coverage to expired_state and save to history.
                        # Get count of claim for this coverage
                        claim_count = Claim.objects.filter(coverage_id = coverage_id).count()

                        # Change the datetime field to timestamp
                        start_at = coverage_start_at
                        if start_at is None:
                            start_at_timestamp = start_at
                        else:
                            start_at_timestamp = start_at.timestamp()
                        end_at = coverage_end_at
                        if end_at is None:
                            end_at_timestamp = end_at
                        else:
                            end_at_timestamp = end_at.timestamp()

                        current_datetime = datetime.datetime.now()

                        if coverage.state != 1 and coverage.state != 4:
                            if end_at_timestamp != None:
                                if current_datetime.timestamp() >= (coverage_end_at.timestamp()):
                                    coverage.state = 4
                                    coverage.save()

                                    history_content = {}

                                    history_content['id'] = coverage.id
                                    history_content['name'] = coverage.name
                                    history_content['user_id'] = coverage.user_id
                                    history_content['latitude'] = coverage.latitude
                                    history_content['longitude'] = coverage.longitude
                                    history_content['address'] = coverage.address
                                    history_content['company_id'] = coverage.company_id
                                    history_content['start_at'] = int(start_at_timestamp)
                                    history_content['end_at'] = int(end_at_timestamp)
                                    history_content['video_mile'] = str(coverage.video_mile)
                                    history_content['video_vehicle'] = str(coverage.video_vehicle)
                                    history_content['image_mile'] = str(coverage.image_mile)
                                    history_content['image_vehicle'] = str(coverage.image_vehicle)
                                    history_content['state'] = coverage.state
                                    history_content['claim_count'] = claim_count;

                                    json_content = json.dumps(history_content)

                                    history_data = History(user_id=userInfo.id, type="Coverage", content=str(json_content))
                                    history_data.save()

                        coverage_state = coverage.state

                        if coverage_state == None or coverage_state == 1 or coverage_state == 2:
                            time_left = coverage_end_at.timestamp() - current_datetime.timestamp()
                        else:
                            time_left = 0;

                        company = Company.objects.filter(id = coverage_company_id).first()

                        if company != None:

                            company_id = company.id
                            company_name = company.name
                            company_latitude = company.latitude
                            company_longitude = company.longitude
                            company_address = company.address
                            company_type = company.type

                            response_company = {
                                "id": company_id,
                                "name": company_name,
                                "latitude": company_latitude,
                                "longitude": company_longitude,
                                "address": company_address,
                                "type": company_type
                            }
                        else:
                            response_company = None

                        response_coverage = {
                            "id": coverage_id,
                            "name": coverage_name,
                            "latitude": coverage_latitude,
                            "longitude": coverage_longitude,
                            "address": coverage_address,
                            "company": response_company,
                            "start_at": int(start_at_timestamp),
                            "end_at": int(end_at_timestamp),
                            "video_mile": str(coverage_video_mile),
                            "video_vehicle": str(coverage_video_vehicle),
                            "image_mile": str(coverage_image_mile),
                            "image_vehicle": str(coverage_image_vehicle),
                            "state": coverage_state,
                            "time_left": int(time_left),
                            "claim_count": claim_count}

                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "true", "data": {
                                "message": "Getting active coverage succeeded.",
                                "coverage": response_coverage,
                                "pay_state": pay_state,
                                "refresh_user": resultCheckingResult.get("refresh_user"),
                                "token_state": "valid"}}
                        else:
                            response_data = {"success": "true", "data": {
                                "message": "Getting active coverage succeeded.",
                                "coverage": response_coverage,
                                "pay_state": pay_state,
                                "token_state": "valid"}}

                        return Response(response_data, status=status.HTTP_200_OK)

                    else:
                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false", "data": {
                                "message": "The active coverage doesn't exist.",
                                "pay_state": pay_state,
                                "token_state": "valid",
                                "refresh_user": resultCheckingResult.get("refresh_user")}}
                        else:
                            response_data = {"success": "false", "data": {
                                "message": "The active coverage doesn't exist.",
                                "pay_state": pay_state,
                                "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)

                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Cancel coverage
class CancelCoverage(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")
        coverage_id = request.data.get("coverage_id")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    coverage = Coverage.objects.filter(id = coverage_id).first()

                    if coverage != None:

                        currentDateTime = datetime.datetime.now()
                        timestamp_current_datetime = currentDateTime.timestamp()

                        coverage.state = 3
                        coverage.save()

                        claim_count = Claim.objects.filter(coverage_id = coverage_id).count()

                        history_content = {}

                        history_content['id'] = coverage.id
                        history_content['name'] = coverage.name
                        history_content['user_id'] = coverage.user_id
                        history_content['latitude'] = coverage.latitude
                        history_content['longitude'] = coverage.longitude
                        history_content['address'] = coverage.address
                        history_content['company_id'] = coverage.company_id

                        # Change the datetime field to timestamp
                        start_at = coverage.starting_at
                        if start_at != None:
                            history_content['start_at'] = int(start_at.timestamp())
                        else:
                            history_content['start_at'] = None
                        end_at = coverage.ending_at
                        if end_at != None:
                            history_content['end_at'] = int(end_at.timestamp())
                        else:
                            history_content['end_at'] = None
                        history_content['video_mile'] = str(coverage.video_mile)
                        history_content['video_vehicle'] = str(coverage.video_vehicle)
                        history_content['image_mile'] = str(coverage.image_mile)
                        history_content['image_vehicle'] = str(coverage.image_vehicle)
                        history_content['state'] = coverage.state
                        history_content['claim_count'] = claim_count;
                        history_content['cancel_date'] = timestamp_current_datetime

                        history_json_content = json.dumps(history_content)

                        history_data = History(user_id = userInfo.id, type = "Coverage", content = history_json_content)
                        history_data.save()

                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "true", "data": {
                                "message": "The coverage was cancelled successfully.",
                                "refresh_user": resultCheckingResult.get("refresh_user"),
                                "token_state": "valid"}}
                        else:
                            response_data = {"success": "true", "data": {
                                "message": "The coverage was cancelled successfully.",
                                "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false", "data": {"message": "The coverage information doesn't exist.", "token_state": "valid", "refresh_user": resultCheckingResult.get("refresh_user")}}
                            return Response(response_data, status=status.HTTP_200_OK)
                        else:
                            response_data = {"success": "false", "data": {"message": "The coverage information doesn't exist.", "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Confirm expired coverage
class ConfirmExpiredCoverage(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")
        coverage_id = request.data.get("coverage_id")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    coverage = Coverage.objects.filter(id = coverage_id).first()

                    if coverage != None:
                        coverage.state = 5
                        coverage.save()

                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "true", "data": {
                                "message": "The expired coverage was confirmed successfully.",
                                "refresh_user": resultCheckingResult.get("refresh_user"),
                                "token_state": "valid"}}
                        else:
                            response_data = {"success": "true", "data": {
                                "message": "The expired coverage was confirmed successfully.",
                                "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false", "data": {"message": "The coverage information doesn't exist.", "token_state": "valid", "refresh_user": resultCheckingResult.get("refresh_user")}}
                            return Response(response_data, status=status.HTTP_200_OK)
                        else:
                            response_data = {"success": "false", "data": {"message": "The coverage information doesn't exist.", "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)


# Add claim
class AddClaimView(APIView):

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")
        coverage_id = request.data.get("coverage_id")
        claim_id = request.data.get("claim_id")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    # Add user_id to the request data to save as a model field
                    # _mutable = request.data._mutable
                    # request_data = request.data
                    # request_data._mutable = True
                    # request_data['user_id'] = existed_user.id
                    # request_data._mutable = _mutable

                    files = request.FILES

                    try:
                        videoClaim = files['video']
                    except:
                        videoClaim = None
                    try:
                        imageClaim = files['image']
                    except:
                        imageClaim = None

                    add_claim_serializer = AddClaimSerializer(data = request.data)
                    if (add_claim_serializer.is_valid()):

                        if claim_id != None:

                            claim = Claim.objects.filter(coverage_id = coverage_id).filter(id = claim_id).first()

                            if request.data.get("latitude") != None:
                                claim.latitude = request.data.get("latitude")
                            if request.data.get("longitude") != None:
                                claim.longitude = request.data.get("longitude")
                            if request.data.get("address") != None:
                                claim.address = unquote(request.data.get("address"))
                            if request.data.get("coverage_id") != None:
                                claim.coverage_id = request.data.get("coverage_id")
                            if request.data.get("what_happened") != None:
                                claim.what_happened = unquote(request.data.get("what_happened"))
                            if request.data.get("time_happened") != None:
                                claim.time_happened = request.data.get("time_happened")
                            if request.data.get("damaged_part") != None:
                                claim.damaged_part = request.data.get("damaged_part")
                            if videoClaim != None:
                                claim.video = videoClaim
                            elif request.data.get("video") != None:
                                claim.video = request.data.get("video")
                            if imageClaim != None:
                                claim.image = imageClaim
                            elif request.data.get("image") != None:
                                claim.image = request.data.get("image")
                            if request.data.get("note") != None:
                                claim.note = unquote(request.data.get("note"))
                            if request.data.get("state") != None:
                                claim.state = request.data.get("state")

                            claim.save()
                        else:
                            obj = add_claim_serializer.save();
                            claim = Claim.objects.filter(id = obj.id).first()
                            claim.name = userInfo.user_app_id + '-' + func_generate_claim_id()
                            claim.save()

                        # For saving content to history table (not date_time_happenend)
                        if request.data.get("time_happened") != None:
                            time_happenend = int(request.data.get("time_happened"))
                            datetime_happened = datetime.datetime.utcfromtimestamp(time_happenend)
                        else:
                            datetime_happened = None

                        claim.user_id = userInfo.id
                        claim.date_time_happened = datetime_happened

                        if request.data.get("address") != None:
                            claim.address = unquote(request.data.get("address"))
                        if request.data.get("what_happened") != None:
                            claim.what_happened = unquote(request.data.get("what_happened"))
                        if request.data.get("note") != None:
                            claim.note = unquote(request.data.get("note"))

                        claim.save();

                        history_content = {}

                        history_content['id'] = claim.id
                        history_content['name'] = claim.name
                        history_content['user_id'] = claim.user_id
                        history_content['latitude'] = claim.latitude
                        history_content['longitude'] = claim.longitude
                        history_content['address'] = claim.address
                        history_content['coverage_id'] = claim.coverage_id
                        if claim.time_happened != None:
                            history_content['time_happened'] = int(claim.time_happened)
                        else:
                            history_content['time_happened'] = None
                        history_content['damaged_part'] = claim.damaged_part
                        history_content['video'] = str(claim.video)
                        history_content['image'] = str(claim.image)
                        history_content['note'] = claim.note
                        history_content['state'] = claim.state

                        json_content = json.dumps(history_content)

                        history_data = History(user_id = userInfo.id, type = "Claim", content = str(json_content))
                        history_data.save()

                        coverage = Coverage.objects.filter(id = claim.coverage_id).first()
                        claim_count = Claim.objects.filter(coverage_id = claim.coverage_id).count()
                        history_content = {}

                        history_content['id'] = coverage.id
                        history_content['name'] = coverage.name
                        history_content['user_id'] = coverage.user_id
                        history_content['latitude'] = coverage.latitude
                        history_content['longitude'] = coverage.longitude
                        history_content['address'] = coverage.address
                        history_content['company_id'] = coverage.company_id

                        # Change the datetime field to timestamp
                        start_at = coverage.starting_at
                        if start_at != None:
                            history_content['start_at'] = int(start_at.timestamp())
                        else:
                            history_content['start_at'] = None
                        end_at = coverage.ending_at
                        if end_at != None:
                            history_content['end_at'] = int(end_at.timestamp())
                        else:
                            history_content['end_at'] = None
                        history_content['video_mile'] = str(coverage.video_mile)
                        history_content['video_vehicle'] = str(coverage.video_vehicle)
                        history_content['image_mile'] = str(coverage.image_mile)
                        history_content['image_vehicle'] = str(coverage.image_vehicle)
                        history_content['state'] = coverage.state
                        history_content['claim_count'] = claim_count;

                        json_content = json.dumps(history_content)

                        history_data = History(user_id = userInfo.id, type = "Coverage", content = str(json_content))
                        history_data.save()

                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "true", "data": {
                                    "message": "Adding claim succeeded.",
                                    "claim_id": claim.id,
                                    "token_state": "valid",
                                    "refresh_user": resultCheckingResult.get("refresh_user")}}
                        else:
                            response_data = {"success": "true", "data": {"message": "Adding claim succeeded.", "claim_id": claim.id, "token_state": "valid"}}

                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false", "data": {"message": add_claim_serializer.errors, "token_state": "valid", "refresh_user": resultCheckingResult.get("refresh_user")}}
                        else:
                            response_data = {"success": "false", "data": {"message": add_claim_serializer.errors, "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)

            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Get claim list
class GetClaimListView(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")
        coverage_id = request.data.get("coverage_id")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:
                    if coverage_id != None:
                        claim_list = Claim.objects.filter(user_id = userInfo.id).filter(coverage_id = coverage_id).order_by('-updated_at').all()

                        response_claim_list = []

                        for claim in claim_list:

                            record = {
                                "id" : claim.id,
                                "name" : claim.name,
                                "user_id" : claim.user_id,
                                "what_happenend" : claim.what_happened,
                                "time_happened" : claim.time_happened,
                                "latitude" : claim.latitude,
                                "longitude" : claim.longitude,
                                "address" : claim.address,
                                "damaged_part" : claim.damaged_part,
                                "video" : str(claim.video),
                                "image": str(claim.image),
                                "note" : claim.note,
                                "state" : claim.state
                            }

                            response_claim_list.append(record)

                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "true", "data": {
                                "message": "Getting claim list succeeded.",
                                "claimList": response_claim_list,
                                "token_state": "valid",
                                "refresh_user": resultCheckingResult.get("refresh_user")}}
                        else:
                            response_data = {"success": "true", "data": {
                                "message": "Getting claim list succeeded.",
                                "claimList": response_claim_list,
                                "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false", "data": {"message": "The coverage id is invalid.", "token_state": "valid"}}
                        else:
                            response_data = {"success": "false", "data": {"message": "The coverage id is invalid.", "token_state": "valid", "refresh_user": resultCheckingResult.get("refresh_user")}}
                        return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)


# Remove claim
class RemoveClaimView(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")
        claim_id = request.data.get("claim_id")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    claim = Claim.objects.filter(id = claim_id).first()

                    if claim != None:
                        if claim.state != 1:
                            if resultCheckingResult.get("refresh_user") != None:
                                response_data = {"success": "false", "data": {"message": "The claim can't be removed because it's state isn't incomplete.", "token_state": "valid", "refresh_user": resultCheckingResult.get("refresh_user")}}
                            else:
                                response_data = {"success": "false", "data": {"message": "The claim can't be removed because it's state isn't incomplete.", "token_state": "valid"}}
                            return Response(response_data, status=status.HTTP_200_OK)

                        history_content = {}

                        history_content['id'] = claim.id
                        history_content['name'] = claim.name
                        history_content['user_id'] = claim.user_id
                        history_content['latitude'] = claim.latitude
                        history_content['longitude'] = claim.longitude
                        history_content['address'] = claim.address
                        history_content['coverage_id'] = claim.coverage_id
                        if claim.time_happened != None:
                            history_content['time_happened'] = int(claim.time_happened)
                        else:
                            history_content['time_happened'] = None
                        history_content['damaged_part'] = claim.damaged_part
                        history_content['video'] = str(claim.video)
                        history_content['image'] = str(claim.image)
                        history_content['note'] = claim.note
                        history_content['state'] = claim.state  # Set cancel state

                        history_json_content = json.dumps(history_content)

                        history_data = History(user_id = userInfo.id, type = "Claim", content = history_json_content)
                        history_data.save()

                        coverage = Coverage.objects.filter(id = claim.coverage_id).first()
                        claim_count = Claim.objects.filter(coverage_id = claim.coverage_id).count()
                        history_content = {}

                        history_content['id'] = coverage.id
                        history_content['name'] = coverage.name
                        history_content['user_id'] = coverage.user_id
                        history_content['latitude'] = coverage.latitude
                        history_content['longitude'] = coverage.longitude
                        history_content['address'] = coverage.address
                        history_content['company_id'] = coverage.company_id

                        # Change the datetime field to timestamp
                        start_at = coverage.starting_at
                        if start_at != None:
                            history_content['start_at'] = int(start_at.timestamp())
                        else:
                            history_content['start_at'] = None
                        end_at = coverage.ending_at
                        if end_at != None:
                            history_content['end_at'] = int(end_at.timestamp())
                        else:
                            history_content['end_at'] = None
                        history_content['video_mile'] = str(coverage.video_mile)
                        history_content['video_vehicle'] = str(coverage.video_vehicle)
                        history_content['image_mile'] = str(coverage.image_mile)
                        history_content['image_vehicle'] = str(coverage.image_vehicle)
                        history_content['state'] = coverage.state
                        history_content['claim_count'] = (claim_count - 1);

                        history_json_content = json.dumps(history_content)

                        history_data = History(user_id = userInfo.id, type = "Coverage", content = str(history_json_content))
                        history_data.save()

                        claim.delete()

                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "true", "data": {
                                "message": "The claim was removed successfully.",
                                "token_state": "valid",
                                "refresh_user": resultCheckingResult.get("refresh_user")}}
                        else:
                            response_data = {"success": "true", "data": {
                                "message": "The claim was removed successfully.",
                                "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        if resultCheckingResult.get("refresh_user") != None:
                            response_data = {"success": "false", "data": {"message": "The claim data doesn't exist.", "refresh_user": resultCheckingResult.get("refresh_user"), "token_state": "valid"}}
                        else:
                            response_data = {"success": "false", "data": {"message": "The claim data doesn't exist.", "token_state": "valid"}}
                        return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)


# Get history list (Coverage, Claim, Payment)
class GetHistoryListView(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    history_list = History.objects.filter(user_id = userInfo.id).order_by('-updated_at').all()

                    response_history_list = []

                    for history in history_list:
                        history_id = history.id
                        history_type = history.type
                        history_content = history.content

                        json_content = json.loads(history_content)

                        record = {"id": history_id, "type": history_type, "content": json_content}
                        response_history_list.append(record)

                    if resultCheckingResult.get("refresh_user") != None:
                        response_data = {"success": "true", "data": {
                            "message": "Getting history list succeeded.",
                            "historyList": response_history_list,
                            "token_state": "valid",
                            "refresh_user": resultCheckingResult.get("refresh_user")}}
                    else:
                        response_data = {"success": "true", "data": {
                            "message": "Getting history list succeeded.",
                            "historyList": response_history_list,
                            "token_state": "valid"}}
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
                    return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
                return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}
            return Response(response_data, status=status.HTTP_200_OK)

# Get company list near user
class GetNearCompanyListView(APIView):

    def post(self, request):

        # Get user_id from access_token
        access_token = request.data.get("access_token")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        # Access token validation
        resultCheckingResult = checkAccessToken(access_token)

        if resultCheckingResult != None:

            if resultCheckingResult.get("state") == 'valid':

                userInfo = User.objects.filter(id = resultCheckingResult.get("user_id")).first()

                if userInfo != None:

                    # User's position
                    pos_one = (latitude, longitude)

                    company_list = Company.objects.all()

                    response_company_list = []

                    for company in company_list:
                        company_latitude = company.latitude
                        company_longitude = company.longitude

                        # Company's position
                        pos_two = (company_latitude, company_longitude)

                        # Unit: Km
                        company_distance_from_user = geopy.distance.vincenty(pos_one, pos_two).kilometers
                        company_id = company.id
                        company_name = company.name
                        company_type = company.type

                        record = {"id": company_id, "name": company_name, "type": company_type, "distance": company_distance_from_user}
                        response_company_list.append(record)

                    def extract_distance(json):
                        try:
                            # Also convert to int since update_time will be string.  When comparing
                            # strings, "10" is smaller than "2".
                            return float(json['distance'])
                        except KeyError:
                            return 0

                    response_company_list.sort(key = extract_distance, reverse = False)

                    if resultCheckingResult.get("refresh_user") != None:
                        response_data = {"success": "true", "data": {
                            "message": "Getting company list succeeded.",
                            "companyList": response_company_list,
                            "token_state": "valid",
                            "refresh_user": resultCheckingResult.get("refresh_user")}}
                    else:
                        response_data = {"success": "true", "data": {
                            "message": "Getting company list succeeded.",
                            "companyList": response_company_list,
                            "token_state": "valid"}}
                else:
                    response_data = {"success": "false", "data": {"message": "The access token is invalid.", "token_state": "invalid"}}
            else:
                response_data = {"success": "false", "data": {"message": "The access token is invalid.",
                                 "token_state": "invalid"}}
        else:
            response_data = {"success": "false", "data": {"message": "There'a problem with checking token.", "token_state": "invalid"}}

        return Response(response_data, status=status.HTTP_200_OK)

class FileUploadTestView(APIView):

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):

        file_serializer = FileUploadTestSerializer(data=request.data)
        if file_serializer.is_valid():
            file_serializer.save()
            return Response(file_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(file_serializer.errors, status=status.HTTP_200_OK)

class GetSupportInfoVIew(APIView):

    def post(self, request):

        support_info = Support.objects.first()

        if support_info == None:
            response_data = {"success": "false", "data": {"message": "The support information does not exist."}}
            return Response(response_data, status=status.HTTP_200_OK)

        responseSupportInfo = {"phone_number": support_info.phone_number}

        response_data = {"success": "true", "data": {
            "message": "Getting support info succeeded.",
            "support_info": responseSupportInfo}}

        return Response(response_data, status=status.HTTP_200_OK)