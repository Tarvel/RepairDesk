"""
Management command to set up initial user groups and permissions.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from repairs.models import RepairTicket


class Command(BaseCommand):
    help = 'Set up initial user groups with appropriate permissions'

    def handle(self, *args, **options):
        # Get RepairTicket content type
        ticket_ct = ContentType.objects.get_for_model(RepairTicket)
        
        # Get custom permissions
        can_diagnose = Permission.objects.get(codename='can_diagnose', content_type=ticket_ct)
        can_approve = Permission.objects.get(codename='can_approve', content_type=ticket_ct)
        can_qc = Permission.objects.get(codename='can_qc', content_type=ticket_ct)
        can_collect = Permission.objects.get(codename='can_collect', content_type=ticket_ct)
        
        # Create groups
        frontdesk, created = Group.objects.get_or_create(name='Front Desk')
        if created:
            frontdesk.permissions.add(can_collect)
            self.stdout.write(self.style.SUCCESS('Created "Front Desk" group'))
        else:
            self.stdout.write('"Front Desk" group already exists')
        
        technician, created = Group.objects.get_or_create(name='Technician')
        if created:
            technician.permissions.add(can_diagnose)
            self.stdout.write(self.style.SUCCESS('Created "Technician" group'))
        else:
            self.stdout.write('"Technician" group already exists')
        
        supervisor, created = Group.objects.get_or_create(name='Supervisor')
        if created:
            supervisor.permissions.add(can_approve, can_qc, can_diagnose)
            self.stdout.write(self.style.SUCCESS('Created "Supervisor" group'))
        else:
            self.stdout.write('"Supervisor" group already exists')
        
        self.stdout.write(self.style.SUCCESS('\nGroup setup complete!'))
        self.stdout.write('\nGroup permissions:')
        self.stdout.write('  Front Desk: can_collect (Intake/Collection)')
        self.stdout.write('  Technician: can_diagnose (Diagnosis/Repair)')
        self.stdout.write('  Supervisor: can_diagnose, can_approve, can_qc (Full pipeline)')
