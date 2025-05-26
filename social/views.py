from django.dispatch import receiver
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from .models import Friendship, Blacklist
from .forms import AddFriendForm, AcceptFriendRequestForm
from django.conf import settings
from accounts.models import CustomUser  # 导入正确的用户模型

class FriendListView(LoginRequiredMixin, View):
    """好友列表视图，需要用户登录"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get(self, request):
        try:
            # 获取当前用户的好友列表
            # 注意：这里使用了具体的用户模型，而不是settings.AUTH_USER_MODEL
            friends = CustomUser.objects.filter(
                Q(sent_friend_requests__to_user=request.user, sent_friend_requests__accepted_at__isnull=False) |
                Q(received_friend_requests__from_user=request.user, received_friend_requests__accepted_at__isnull=False)
            ).distinct()
            
            # 获取发送和接收的好友请求
            sent_requests = Friendship.objects.filter(from_user=request.user, accepted_at__isnull=True)
            received_requests = Friendship.objects.filter(to_user=request.user, accepted_at__isnull=True)
            
            # 获取黑名单用户
            blacklisted_users = CustomUser.objects.filter(
                blocked_by__user=request.user
            ).distinct()
            
            # 准备表单
            add_friend_form = AddFriendForm()
            accept_form = AcceptFriendRequestForm()
            
            context = {
                'friends': friends,
                'sent_requests': sent_requests,
                'received_requests': received_requests,
                'blacklisted_users': blacklisted_users,
                'add_friend_form': add_friend_form,
                'accept_form': accept_form,
            }
            
            return render(request, 'social/friend_list.html', context)
        except Exception as e:
            messages.error(request, f'加载好友列表时出错: {str(e)}')
            return render(request, 'social/friend_list.html', {'error': True})
    
    def post(self, request):
        if 'add_friend' in request.POST:
            form = AddFriendForm(request.POST)
            if form.is_valid():
                target_user = form.cleaned_data['target_user_identifier']
                
                # 添加日志以检查target_user
                print(f"Target user: {target_user}, type: {type(target_user)}")
                
                # 检查目标用户是否在黑名单中
                if Blacklist.objects.filter(
                    Q(user=request.user, blocked_user=target_user) | 
                    Q(user=target_user, blocked_user=request.user)
                ).exists():
                    messages.error(request, f'无法添加好友，用户在黑名单中。')
                elif target_user == request.user:
                    messages.error(request, '你不能添加自己为好友。')
                elif Friendship.objects.filter(
                    Q(from_user=request.user, to_user=target_user) |
                    Q(from_user=target_user, to_user=request.user, accepted_at__isnull=False)
                ).exists():
                    messages.info(request, f'你和{target_user.username}已是好友或已发送请求。')
                elif Friendship.objects.filter(from_user=target_user, to_user=request.user, accepted_at__isnull=True).exists():
                    messages.info(request, f'{target_user.username}已向你发送好友申请。')
                else:
                    Friendship.objects.create(from_user=request.user, to_user=target_user)
                    messages.success(request, f'好友申请已发送至{target_user.username}')
            else:
                messages.error(request, '发送失败，请检查邮箱或用户名。')
        
        elif 'accept_friend' in request.POST:
            try:
                request_id = request.POST.get('request_id')
                if not request_id:
                    messages.error(request, '缺少好友请求ID')
                    return redirect('social:friend_list')
                
                friend_request = get_object_or_404(
                    Friendship, 
                    id=request_id, 
                    to_user=request.user, 
                    accepted_at__isnull=True
                )
                
                friend_request.accept()
                messages.success(request, f'已接受来自{friend_request.from_user.username}的好友申请。')
            except Friendship.DoesNotExist:
                messages.error(request, '找不到该好友请求。')
            except Exception as e:
                messages.error(request, f'接受好友请求时出错: {str(e)}')
        
        elif 'reject_friend' in request.POST:
            try:
                request_id = request.POST.get('request_id')
                if not request_id:
                    messages.error(request, '缺少好友请求ID')
                    return redirect('social:friend_list')
                
                friend_request = get_object_or_404(
                    Friendship, 
                    id=request_id, 
                    to_user=request.user, 
                    accepted_at__isnull=True
                )
                
                from_user = friend_request.from_user
                friend_request.delete()
                messages.success(request, f'已拒绝来自{from_user.username}的好友申请。')
            except Friendship.DoesNotExist:
                messages.error(request, '找不到该好友请求。')
            except Exception as e:
                messages.error(request, f'拒绝好友请求时出错: {str(e)}')
        
        elif 'unblock_user' in request.POST:
            try:
                user_id = request.POST.get('user_id')
                if not user_id:
                    messages.error(request, '缺少用户ID')
                    return redirect('social:friend_list')
                
                blocked_user = get_object_or_404(CustomUser, id=user_id)
                blacklist_entry = Blacklist.objects.filter(user=request.user, blocked_user=blocked_user).first()
                
                if blacklist_entry:
                    blacklist_entry.delete()
                    messages.success(request, f'已将 {blocked_user.username} 从黑名单中移除')
                else:
                    messages.error(request, '该用户不在你的黑名单中。')
            except CustomUser.DoesNotExist:
                messages.error(request, '找不到该用户。')
            except Exception as e:
                messages.error(request, f'解除拉黑时出错: {str(e)}')
                
        return redirect('social:friend_list')

class FriendProfileView(LoginRequiredMixin, View):
    """好友资料页视图，用于显示好友详细信息并提供删除/拉黑操作"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get(self, request, friend_id):
        try:
            # 获取好友对象
            friend = get_object_or_404(CustomUser, id=friend_id)
            
            # 检查是否是好友关系
            is_friend = Friendship.objects.filter(
                Q(from_user=request.user, to_user=friend, accepted_at__isnull=False) |
                Q(from_user=friend, to_user=request.user, accepted_at__isnull=False)
            ).exists()
            
            if not is_friend:
                messages.error(request, '该用户不是您的好友。')
                return redirect('social:friend_list')
            
            # 获取好友关系建立时间
            friendship = Friendship.objects.filter(
                Q(from_user=request.user, to_user=friend, accepted_at__isnull=False) |
                Q(from_user=friend, to_user=request.user, accepted_at__isnull=False)
            ).first()
            
            friendship_date = friendship.accepted_at if friendship else None
            
            context = {
                'friend': friend,
                'friendship_date': friendship_date,
            }
            
            return render(request, 'social/friend_profile.html', context)
        except Exception as e:
            messages.error(request, f'加载好友资料时出错: {str(e)}')
            return redirect('social:friend_list')
    
    def post(self, request, friend_id):
        try:
            friend = get_object_or_404(CustomUser, id=friend_id)
            
            if 'remove_friend' in request.POST:
                # 查找并删除好友关系
                friendship = Friendship.objects.filter(
                    Q(from_user=request.user, to_user=friend, accepted_at__isnull=False) |
                    Q(from_user=friend, to_user=request.user, accepted_at__isnull=False)
                ).first()
                
                if friendship:
                    friendship.delete()
                    messages.success(request, f'已删除好友: {friend.username}')
                else:
                    messages.error(request, '找不到该好友关系。')
                return redirect('social:friend_list')
            
            elif 'block_user' in request.POST:
                if friend == request.user:
                    messages.error(request, '你不能拉黑自己。')
                elif Blacklist.objects.filter(user=request.user, blocked_user=friend).exists():
                    messages.info(request, f'{friend.username} 已在你的黑名单中。')
                else:
                    # 添加到黑名单
                    Blacklist.objects.create(user=request.user, blocked_user=friend)
                    
                    # 删除好友关系（如果存在）
                    Friendship.objects.filter(
                        Q(from_user=request.user, to_user=friend) |
                        Q(from_user=friend, to_user=request.user)
                    ).delete()
                    
                    messages.success(request, f'已将 {friend.username} 加入黑名单')
                return redirect('social:friend_list')
            
            return redirect('social:friend_profile', friend_id=friend_id)
            
        except CustomUser.DoesNotExist:
            messages.error(request, '找不到该用户。')
        except Exception as e:
            messages.error(request, f'处理请求时出错: {str(e)}')
        
        return redirect('social:friend_list')

# class RejectFriendListView(LoginRequiredMixin, View):pass
# class RemoveFriendListView(LoginRequiredMixin, View):pass