"""twitterlytic URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from .views import (
    HomeView, LogoutView, TwitterReturnView,
    ProfileView, ProfileCountsJSON, ProfileFollowersJSON, ProfileFollowingJSON)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^profile/(?P<slug>[a-z_A-Z0-9]*)/$', ProfileView.as_view(),
        name='profile'),
    url(r'^profile/(?P<slug>[a-z_A-Z0-9]*)/counts.json$',
        ProfileCountsJSON.as_view(),
        name='profile-counts-json'),
    url(r'^profile/(?P<slug>[a-z_A-Z0-9]*)/following-list.json$',
        ProfileFollowingJSON.as_view(),
        name='profile-following-list-json'),
    url(r'^profile/(?P<slug>[a-z_A-Z0-9]*)/followers-list.json$',
        ProfileFollowersJSON.as_view(),
        name='profile-followers-list-json'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),
    url(r'^twitter_return/$', TwitterReturnView.as_view(),
        name='twitter_return'),
]
