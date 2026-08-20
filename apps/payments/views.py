from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.db import models
from apps.payments.models import SubscriptionPlan, UserSubscription
from apps.payments.serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer

class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserSubscription.objects.all().order_by('-created_at')
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAdminUser]

class PaymentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def plans(self, request):
        plans = SubscriptionPlan.objects.all()
        return Response(SubscriptionPlanSerializer(plans, many=True).data)

    @action(detail=False, methods=['post'])
    def sync_status(self, request):
        """
        Endpoint for the mobile app to manually trigger a sync of their RevenueCat status.
        """
        import datetime
        from django.utils import timezone
        
        rc_id = request.data.get('rc_original_app_user_id')
        is_pro = request.data.get('is_pro', False)
        plan_name = request.data.get('plan_name', 'Monthly Pro')
        price = request.data.get('price', 5.00)
        
        user = request.user
        
        if rc_id:
            user.rc_original_app_user_id = rc_id
            
        user.is_pro = is_pro
        user.save()
        
        if is_pro:
            # Create a plan matching the RevenueCat offering
            interval = "month" if "monthly" in plan_name.lower() else "year"
            plan, _ = SubscriptionPlan.objects.get_or_create(
                stripe_price_id=f"rc_{plan_name.lower().replace(' ', '_')}",
                defaults={
                    'name': plan_name,
                    'price': price,
                    'interval': interval
                }
            )
            
            user_sub, _ = UserSubscription.objects.get_or_create(user=user)
            user_sub.plan = plan
            user_sub.status = 'active'
            user_sub.rc_original_app_user_id = rc_id
            user_sub.save()
        else:
            user_sub = UserSubscription.objects.filter(user=user).first()
            if user_sub:
                user_sub.status = 'canceled'
                user_sub.save()
        
        return Response({"is_pro": user.is_pro, "rc_original_app_user_id": user.rc_original_app_user_id})

    @action(detail=False, methods=['post'])
    def create_checkout_session(self, request):
        import stripe
        from django.conf import settings
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_dummy')
        
        plan_id = request.data.get('plan_id')
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"detail": "Invalid subscription plan ID"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': plan.stripe_price_id if plan.stripe_price_id else 'price_dummy',
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri('/dashboard/payments/?session_id={CHECKOUT_SESSION_ID}'),
                cancel_url=request.build_absolute_uri('/dashboard/payments/'),
                client_reference_id=str(request.user.id),
                customer_email=request.user.email,
            )
            return Response({"checkout_url": session.url})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_payment_intent(self, request):
        import stripe
        from django.conf import settings
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_dummy')
        
        plan_id = request.data.get('plan_id')
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"detail": "Invalid subscription plan ID"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Generate customer or retrieve existing
            customer_id = None
            user_sub = UserSubscription.objects.filter(user=request.user).first()
            if user_sub and user_sub.stripe_customer_id:
                customer_id = user_sub.stripe_customer_id
            else:
                customer = stripe.Customer.create(email=request.user.email)
                customer_id = customer.id
                if not user_sub:
                    user_sub = UserSubscription.objects.create(user=request.user, stripe_customer_id=customer_id)
                else:
                    user_sub.stripe_customer_id = customer_id
                    user_sub.save()
                    
            # Create Ephemeral Key for Mobile iOS/Android Stripe SDK
            ephemeral_key = stripe.EphemeralKey.create(
                customer=customer_id,
                stripe_version='2023-10-16',
            )
            
            # Since subscriptions are recurring, Stripe SDK recommends SetupIntent or PaymentIntent (Single charge)
            # For simplicity, if they want a recurring checkout, Checkout Session is best.
            # If native checkout SDK, we create a PaymentIntent for the first cycle
            intent = stripe.PaymentIntent.create(
                amount=int(plan.price * 100),
                currency='usd',
                customer=customer_id,
                payment_method_types=['card'],
                metadata={
                    'user_id': request.user.id,
                    'plan_id': plan.id
                }
            )
            return Response({
                "payment_intent": intent.client_secret,
                "ephemeral_key": ephemeral_key.secret,
                "customer": customer_id,
                "publishable_key": getattr(settings, 'STRIPE_PUBLISHABLE_KEY', 'pk_test_dummy')
            })
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def stripe_webhook(self, request):
        import stripe
        from django.conf import settings
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_dummy')
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None
        
        try:
            if webhook_secret and sig_header:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            else:
                import json
                event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        event_type = event.get('type')
        data_object = event.get('data', {}).get('object', {})
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if event_type == 'checkout.session.completed':
            user_id = data_object.get('client_reference_id')
            customer_id = data_object.get('customer')
            sub_id = data_object.get('subscription')
            
            user = User.objects.filter(id=user_id).first() if user_id else None
            if not user:
                # Fallback to customer email
                email = data_object.get('customer_details', {}).get('email')
                user = User.objects.filter(email=email).first()
                
            if user:
                user.is_pro = True
                user.save()
                
                # Update or create subscription details
                user_sub, _ = UserSubscription.objects.get_or_create(user=user)
                user_sub.stripe_customer_id = customer_id
                user_sub.stripe_subscription_id = sub_id
                user_sub.status = 'active'
                user_sub.save()
                
        elif event_type in ['invoice.payment_succeeded', 'customer.subscription.updated']:
            customer_id = data_object.get('customer')
            sub_id = data_object.get('id') if event_type == 'customer.subscription.updated' else data_object.get('subscription')
            
            user_sub = UserSubscription.objects.filter(stripe_subscription_id=sub_id).first()
            if not user_sub and customer_id:
                user_sub = UserSubscription.objects.filter(stripe_customer_id=customer_id).first()
                
            if user_sub:
                user_sub.user.is_pro = True
                user_sub.user.save()
                user_sub.status = 'active'
                user_sub.save()
                
        elif event_type in ['customer.subscription.deleted', 'invoice.payment_failed']:
            sub_id = data_object.get('id') if event_type == 'customer.subscription.deleted' else data_object.get('subscription')
            user_sub = UserSubscription.objects.filter(stripe_subscription_id=sub_id).first()
            if user_sub:
                user_sub.user.is_pro = False
                user_sub.user.save()
                user_sub.status = 'canceled'
                user_sub.save()
                
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def webhook(self, request):
        """
        RevenueCat Webhook handler.
        Handles INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION events.
        """
        from django.utils import timezone
        import datetime
        
        event = request.data.get('event', {})
        event_type = event.get('type')
        app_user_id = event.get('app_user_id')
        product_id = event.get('product_id')
        price = event.get('price', 0.0)
        expiration_ms = event.get('expiration_at_ms')
        
        if not event_type or not app_user_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
            
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.filter(models.Q(id=app_user_id) | models.Q(rc_original_app_user_id=app_user_id)).first()
            if not user:
                return Response(status=status.HTTP_200_OK) # Ignore if user not found to prevent webhook retries
                
            if event_type in ['INITIAL_PURCHASE', 'RENEWAL']:
                user.is_pro = True
                user.rc_original_app_user_id = app_user_id
                user.save()
                
                # Map to plan
                if product_id:
                    plan_name = "Monthly Pro" if "monthly" in product_id.lower() else "Annual Pro"
                    interval = "month" if "monthly" in product_id.lower() else "year"
                    plan_price = price if price > 0 else (5.00 if interval == 'month' else 49.00)
                    
                    plan, _ = SubscriptionPlan.objects.get_or_create(
                        stripe_price_id=product_id,
                        defaults={
                            'name': plan_name,
                            'price': plan_price,
                            'interval': interval
                        }
                    )
                    
                    user_sub, _ = UserSubscription.objects.get_or_create(user=user)
                    user_sub.plan = plan
                    user_sub.status = 'active'
                    if expiration_ms:
                        user_sub.current_period_end = timezone.make_aware(datetime.datetime.fromtimestamp(expiration_ms / 1000.0))
                    user_sub.rc_original_app_user_id = app_user_id
                    user_sub.save()
                    
            elif event_type in ['CANCELLATION', 'EXPIRATION', 'BILLING_ISSUE']:
                user.is_pro = False
                user.save()
                
                user_sub = UserSubscription.objects.filter(user=user).first()
                if user_sub:
                    user_sub.status = 'canceled'
                    user_sub.save()
                    
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response(status=status.HTTP_200_OK)
