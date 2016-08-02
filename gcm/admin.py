from uuid import UUID
from functools import update_wrapper
from django.contrib import admin
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from .forms import MessageForm
from .models import get_device_model

Device = get_device_model()


class DeviceAdmin(admin.ModelAdmin):
    list_display = ['dev_id', 'name', 'modified_date', 'is_active', 'send_message_url']
    search_fields = ('dev_id', 'name')
    list_filter = ['is_active']
    date_hierarchy = 'modified_date'
    actions = ['send_message_action']

    def get_urls(self):
        from django.conf.urls import url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        gcm_urlpatterns = [
                url(r'^send-message/$', wrap(self.send_message_view),
                    name=self.build_admin_url('send_message'))
                ]
        return gcm_urlpatterns + super(DeviceAdmin, self).get_urls()

    def build_admin_url(self, url_name):
        return '%s_%s_%s' % (self.model._meta.app_label,
                             self.model._meta.model_name,
                             url_name)

    def send_message_url(self, obj):
        return '<a href="send-message/?device_ids=%s">Send message</a>' % (obj.pk,)
    send_message_url.allow_tags = True

    def send_message_view(self, request):
        base_view = 'admin:%s' % self.build_admin_url('changelist')
        device_ids = request.GET.get('device_ids', []).split(',')
        if not device_ids:
            return redirect(base_view)

        form = MessageForm(data=request.POST or None)
        if form.is_valid():
            devices = Device.objects.filter(pk__in=device_ids)
            for device in devices:
                device.send_message(form.cleaned_data['message'])
            self.message_user(request, _('Message was sent.'))
            return redirect(base_view)

        context = {'form': form, 'opts': self.model._meta, 'add': False}
        return render_to_response('gcm/admin/send_message.html', context,
                                  context_instance=RequestContext(request))

    def send_message_action(self, request, queryset):
        ids = queryset.values_list('id', flat=True)
        if isinstance(ids[0], UUID):
            ids = [pk.hex for pk in ids]
        url = 'admin:%s' % self.build_admin_url('send_message')
        resp = redirect(url)
        resp['Location'] += '?device_ids=%s' % ','.join(ids)
        return resp
    send_message_action.short_description = _("Send message")


admin.site.register(Device, DeviceAdmin)
