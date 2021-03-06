from django.db import transaction
from rest_framework import exceptions, serializers

from .models import Domain, Record, Zone


class DomainSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default='NATIVE')
    """
    `NATIVE` replication is the default, unless other operation is specifically
    configured. Native replication basically means that PowerDNS will not send
    out DNS update notifications, nor will react to them. PowerDNS assumes that
    the backend is taking care of replication unaided.  Other options include
    `SLAVE` and `MASTER`.
    """

    @transaction.atomic
    def create(self, validated_data):
        """
        Link user to the created domain through a record in the in the
        intermediate "zones" table.
        """
        domain = super().create(validated_data)

        user = self.context['request'].user
        Zone.objects.create(domain=domain, owner=user.id, zone_templ_id=0)

        return domain

    class Meta:
        lookup_field = 'name'
        model = Domain
        fields = ('name', 'type',)


class RecordSerializer(serializers.ModelSerializer):
    domain = serializers.SlugRelatedField(
        queryset=Domain.objects.all(), slug_field='name'
    )

    def validate_domain(self, domain):
        """
        Check whether is allowed to update records on this domain
        """
        request = self.context['request']
        if not domain.zones.filter(owner=request.user.id).exists():
            raise exceptions.PermissionDenied()

        return domain

    class Meta:
        model = Record
        fields = ('id', 'name', 'type', 'content', 'ttl', 'prio', 'domain')


class ZoneSerializer(serializers.ModelSerializer):

    class Meta:
        model = Zone
        fields = ('domain', 'owner')
