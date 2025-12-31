from rest_framework import serializers
from usermanagement.models import User
from django.contrib.auth import authenticate

class UserRegistrationSerializer(serializers.ModelSerializer):
	password = serializers.CharField(write_only=True)
	password2 = serializers.CharField(write_only=True)
	email = serializers.EmailField(required=True)
	first_name = serializers.CharField(required=True)
	last_name = serializers.CharField(required=True)
	
	class Meta:
		model = User
		fields=['email', 'first_name', 'last_name', 'password', 'password2']
		

	# Validating Password and Confirm Password while Registration
	def validate(self, attrs):
		password = attrs.get('password')
		password2 = attrs.get('password2')
		if password != password2:
			raise serializers.ValidationError("Password and Confirm Password doesn't match")
		return attrs

	def create(self, validated_data):
		validated_data.pop('password2')
		return User.objects.create_user(**validated_data)

class UserLoginSerializer(serializers.ModelSerializer):
	email = serializers.EmailField(max_length=255)
	password = serializers.CharField(write_only=True)
	
	class Meta:
		model = User
		fields = ['email', 'password']
	
	def validate(self, attrs):
		email = attrs.get('email')
		password = attrs.get('password')
		try:
			user = User.objects.get(email=email)
		except User.DoesNotExist:
			raise serializers.ValidationError("User with this email does not exist")
		
		authenticated_user = authenticate(email=email, password=password)
		if not authenticated_user:
			raise serializers.ValidationError("Invalid credentials, try again")
		attrs['user'] = user
		return attrs
	


class UserProfileSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['id', 'email', 'first_name', 'last_name']

class UserChangePasswordSerializer(serializers.Serializer):
	password = serializers.CharField(max_length=255, write_only=True)
	password2 = serializers.CharField(max_length=255, write_only=True)
	class Meta:
		fields = ['password', 'password2']

	def validate(self, attrs):
		password = attrs.get('password')
		password2 = attrs.get('password2')
		user = self.context.get('user')
		if password != password2:
			raise serializers.ValidationError("Password and Confirm Password doesn't match")
		user.set_password(password)
		user.save()
		return attrs
