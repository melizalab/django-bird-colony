# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Species'
        db.create_table(u'birds_species', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('common_name', self.gf('django.db.models.fields.CharField')(max_length=45)),
            ('genus', self.gf('django.db.models.fields.CharField')(max_length=45)),
            ('species', self.gf('django.db.models.fields.CharField')(max_length=45)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=4)),
        ))
        db.send_create_signal(u'birds', ['Species'])

        # Adding model 'Color'
        db.create_table(u'birds_color', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('abbrv', self.gf('django.db.models.fields.CharField')(max_length=3)),
        ))
        db.send_create_signal(u'birds', ['Color'])

        # Adding model 'Status'
        db.create_table(u'birds_status', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('count', self.gf('django.db.models.fields.IntegerField')()),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'birds', ['Status'])

        # Adding model 'Location'
        db.create_table(u'birds_location', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45)),
        ))
        db.send_create_signal(u'birds', ['Location'])

        # Adding model 'Animal'
        db.create_table(u'birds_animal', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('species', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['birds.Species'])),
            ('sex', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('band_color', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['birds.Color'], null=True, blank=True)),
            ('band_number', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('uuid', self.gf('uuidfield.fields.UUIDField')(unique=True, max_length=32, blank=True)),
        ))
        db.send_create_signal(u'birds', ['Animal'])

        # Adding M2M table for field parents on 'Animal'
        m2m_table_name = db.shorten_name(u'birds_animal_parents')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_animal', models.ForeignKey(orm[u'birds.animal'], null=False)),
            ('to_animal', models.ForeignKey(orm[u'birds.animal'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_animal_id', 'to_animal_id'])

        # Adding model 'Event'
        db.create_table(u'birds_event', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('animal', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['birds.Animal'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['birds.Status'], null=True, blank=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['birds.Location'], null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('entered_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'birds', ['Event'])


    def backwards(self, orm):
        # Deleting model 'Species'
        db.delete_table(u'birds_species')

        # Deleting model 'Color'
        db.delete_table(u'birds_color')

        # Deleting model 'Status'
        db.delete_table(u'birds_status')

        # Deleting model 'Location'
        db.delete_table(u'birds_location')

        # Deleting model 'Animal'
        db.delete_table(u'birds_animal')

        # Removing M2M table for field parents on 'Animal'
        db.delete_table(db.shorten_name(u'birds_animal_parents'))

        # Deleting model 'Event'
        db.delete_table(u'birds_event')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'birds.animal': {
            'Meta': {'ordering': "[u'band_color', u'band_number']", 'object_name': 'Animal'},
            'band_color': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['birds.Color']", 'null': 'True', 'blank': 'True'}),
            'band_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['birds.Animal']", 'symmetrical': 'False', 'blank': 'True'}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'species': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['birds.Species']"}),
            'uuid': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32', 'blank': 'True'})
        },
        u'birds.color': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Color'},
            'abbrv': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '12'})
        },
        u'birds.event': {
            'Meta': {'ordering': "[u'date']", 'object_name': 'Event'},
            'animal': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['birds.Animal']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'entered_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['birds.Location']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['birds.Status']", 'null': 'True', 'blank': 'True'})
        },
        u'birds.location': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Location'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45'})
        },
        u'birds.species': {
            'Meta': {'ordering': "[u'common_name']", 'object_name': 'Species'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'common_name': ('django.db.models.fields.CharField', [], {'max_length': '45'}),
            'genus': ('django.db.models.fields.CharField', [], {'max_length': '45'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'species': ('django.db.models.fields.CharField', [], {'max_length': '45'})
        },
        u'birds.status': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Status'},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '16'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['birds']