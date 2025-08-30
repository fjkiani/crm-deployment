Directory structure:
└── fjkiani-crm-deployment/
    ├── README.md
    ├── DEPLOYMENT_SUCCESS.md
    ├── FRAPPE_SETUP_GUIDE.md
    ├── MANIFEST.in
    ├── pyproject.toml
    ├── requirements.txt
    ├── setup.py
    ├── crm/
    │   ├── __init__.py
    │   ├── crowdin.yml
    │   ├── hooks.py
    │   ├── install.py
    │   ├── modules.txt
    │   ├── patches.txt
    │   ├── requirements.txt
    │   ├── uninstall.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── activities.py
    │   │   ├── auth.py
    │   │   ├── comment.py
    │   │   ├── contact.py
    │   │   ├── dashboard.py
    │   │   ├── demo.py
    │   │   ├── doc.py
    │   │   ├── notifications.py
    │   │   ├── onboarding.py
    │   │   ├── session.py
    │   │   ├── settings.py
    │   │   ├── todo.py
    │   │   ├── user.py
    │   │   ├── views.py
    │   │   └── whatsapp.py
    │   ├── config/
    │   │   └── __init__.py
    │   ├── fcrm/
    │   │   ├── __init__.py
    │   │   ├── doctype/
    │   │   │   ├── __init__.py
    │   │   │   ├── crm_call_log/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_call_log.js
    │   │   │   │   ├── crm_call_log.json
    │   │   │   │   ├── crm_call_log.py
    │   │   │   │   └── test_crm_call_log.py
    │   │   │   ├── crm_communication_status/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_communication_status.js
    │   │   │   │   ├── crm_communication_status.json
    │   │   │   │   ├── crm_communication_status.py
    │   │   │   │   └── test_crm_communication_status.py
    │   │   │   ├── crm_contacts/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_contacts.json
    │   │   │   │   └── crm_contacts.py
    │   │   │   ├── crm_dashboard/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_dashboard.js
    │   │   │   │   ├── crm_dashboard.json
    │   │   │   │   ├── crm_dashboard.py
    │   │   │   │   └── test_crm_dashboard.py
    │   │   │   ├── crm_deal/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── api.py
    │   │   │   │   ├── crm_deal.js
    │   │   │   │   ├── crm_deal.json
    │   │   │   │   ├── crm_deal.py
    │   │   │   │   └── test_crm_deal.py
    │   │   │   ├── crm_deal_status/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_deal_status.js
    │   │   │   │   ├── crm_deal_status.json
    │   │   │   │   ├── crm_deal_status.py
    │   │   │   │   └── test_crm_deal_status.py
    │   │   │   ├── crm_dropdown_item/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_dropdown_item.json
    │   │   │   │   └── crm_dropdown_item.py
    │   │   │   ├── crm_exotel_settings/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_exotel_settings.js
    │   │   │   │   ├── crm_exotel_settings.json
    │   │   │   │   ├── crm_exotel_settings.py
    │   │   │   │   └── test_crm_exotel_settings.py
    │   │   │   ├── crm_fields_layout/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_fields_layout.js
    │   │   │   │   ├── crm_fields_layout.json
    │   │   │   │   ├── crm_fields_layout.py
    │   │   │   │   └── test_crm_fields_layout.py
    │   │   │   ├── crm_form_script/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_form_script.js
    │   │   │   │   ├── crm_form_script.json
    │   │   │   │   ├── crm_form_script.py
    │   │   │   │   └── test_crm_form_script.py
    │   │   │   ├── crm_global_settings/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_global_settings.js
    │   │   │   │   ├── crm_global_settings.json
    │   │   │   │   ├── crm_global_settings.py
    │   │   │   │   └── test_crm_global_settings.py
    │   │   │   ├── crm_holiday/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_holiday.json
    │   │   │   │   └── crm_holiday.py
    │   │   │   ├── crm_holiday_list/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_holiday_list.js
    │   │   │   │   ├── crm_holiday_list.json
    │   │   │   │   ├── crm_holiday_list.py
    │   │   │   │   └── test_crm_holiday_list.py
    │   │   │   ├── crm_industry/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_industry.js
    │   │   │   │   ├── crm_industry.json
    │   │   │   │   ├── crm_industry.py
    │   │   │   │   └── test_crm_industry.py
    │   │   │   ├── crm_invitation/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_invitation.js
    │   │   │   │   ├── crm_invitation.json
    │   │   │   │   ├── crm_invitation.py
    │   │   │   │   └── test_crm_invitation.py
    │   │   │   ├── crm_lead/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_lead.js
    │   │   │   │   ├── crm_lead.json
    │   │   │   │   ├── crm_lead.py
    │   │   │   │   └── test_crm_lead.py
    │   │   │   ├── crm_lead_source/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_lead_source.js
    │   │   │   │   ├── crm_lead_source.json
    │   │   │   │   ├── crm_lead_source.py
    │   │   │   │   └── test_crm_lead_source.py
    │   │   │   ├── crm_lead_status/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_lead_status.js
    │   │   │   │   ├── crm_lead_status.json
    │   │   │   │   ├── crm_lead_status.py
    │   │   │   │   └── test_crm_lead_status.py
    │   │   │   ├── crm_lost_reason/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_lost_reason.js
    │   │   │   │   ├── crm_lost_reason.json
    │   │   │   │   ├── crm_lost_reason.py
    │   │   │   │   └── test_crm_lost_reason.py
    │   │   │   ├── crm_notification/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_notification.js
    │   │   │   │   ├── crm_notification.json
    │   │   │   │   ├── crm_notification.py
    │   │   │   │   └── test_crm_notification.py
    │   │   │   ├── crm_organization/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_organization.js
    │   │   │   │   ├── crm_organization.json
    │   │   │   │   ├── crm_organization.py
    │   │   │   │   └── test_crm_organization.py
    │   │   │   ├── crm_product/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_product.js
    │   │   │   │   ├── crm_product.json
    │   │   │   │   ├── crm_product.py
    │   │   │   │   └── test_crm_product.py
    │   │   │   ├── crm_products/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_products.json
    │   │   │   │   └── crm_products.py
    │   │   │   ├── crm_service_day/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_service_day.json
    │   │   │   │   └── crm_service_day.py
    │   │   │   ├── crm_service_level_agreement/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_service_level_agreement.js
    │   │   │   │   ├── crm_service_level_agreement.json
    │   │   │   │   ├── crm_service_level_agreement.py
    │   │   │   │   ├── test_crm_service_level_agreement.py
    │   │   │   │   └── utils.py
    │   │   │   ├── crm_service_level_priority/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_service_level_priority.js
    │   │   │   │   ├── crm_service_level_priority.json
    │   │   │   │   ├── crm_service_level_priority.py
    │   │   │   │   └── test_crm_service_level_priority.py
    │   │   │   ├── crm_status_change_log/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_status_change_log.json
    │   │   │   │   └── crm_status_change_log.py
    │   │   │   ├── crm_task/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_task.js
    │   │   │   │   ├── crm_task.json
    │   │   │   │   ├── crm_task.py
    │   │   │   │   └── test_crm_task.py
    │   │   │   ├── crm_telephony_agent/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_telephony_agent.js
    │   │   │   │   ├── crm_telephony_agent.json
    │   │   │   │   ├── crm_telephony_agent.py
    │   │   │   │   └── test_crm_telephony_agent.py
    │   │   │   ├── crm_telephony_phone/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_telephony_phone.json
    │   │   │   │   └── crm_telephony_phone.py
    │   │   │   ├── crm_territory/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_territory.js
    │   │   │   │   ├── crm_territory.json
    │   │   │   │   ├── crm_territory.py
    │   │   │   │   └── test_crm_territory.py
    │   │   │   ├── crm_twilio_settings/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_twilio_settings.js
    │   │   │   │   ├── crm_twilio_settings.json
    │   │   │   │   ├── crm_twilio_settings.py
    │   │   │   │   └── test_crm_twilio_settings.py
    │   │   │   ├── crm_view_settings/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── crm_view_settings.js
    │   │   │   │   ├── crm_view_settings.json
    │   │   │   │   ├── crm_view_settings.py
    │   │   │   │   └── test_crm_view_settings.py
    │   │   │   ├── erpnext_crm_settings/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── erpnext_crm_settings.js
    │   │   │   │   ├── erpnext_crm_settings.json
    │   │   │   │   ├── erpnext_crm_settings.py
    │   │   │   │   └── test_erpnext_crm_settings.py
    │   │   │   ├── fcrm_note/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── fcrm_note.js
    │   │   │   │   ├── fcrm_note.json
    │   │   │   │   ├── fcrm_note.py
    │   │   │   │   └── test_fcrm_note.py
    │   │   │   ├── fcrm_settings/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── fcrm_settings.js
    │   │   │   │   ├── fcrm_settings.json
    │   │   │   │   ├── fcrm_settings.py
    │   │   │   │   └── test_fcrm_settings.py
    │   │   │   └── helpdesk_crm_settings/
    │   │   │       ├── __init__.py
    │   │   │       ├── helpdesk_crm_settings.js
    │   │   │       ├── helpdesk_crm_settings.json
    │   │   │       ├── helpdesk_crm_settings.py
    │   │   │       └── test_helpdesk_crm_settings.py
    │   │   └── workspace/
    │   │       └── frappe_crm/
    │   │           └── frappe_crm.json
    │   ├── integrations/
    │   │   ├── __init__.py
    │   │   ├── api.py
    │   │   ├── exotel/
    │   │   │   └── handler.py
    │   │   └── twilio/
    │   │       ├── api.py
    │   │       ├── twilio_handler.py
    │   │       └── utils.py
    │   ├── overrides/
    │   │   ├── contact.py
    │   │   └── email_template.py
    │   ├── patches/
    │   │   └── v1_0/
    │   │       ├── __init__.py
    │   │       ├── create_default_fields_layout.py
    │   │       ├── create_default_lost_reasons.py
    │   │       ├── create_default_scripts.py
    │   │       ├── create_default_sidebar_fields_layout.py
    │   │       ├── create_email_template_custom_fields.py
    │   │       ├── move_crm_note_data_to_fcrm_note.py
    │   │       ├── move_twilio_agent_to_telephony_agent.py
    │   │       ├── rename_twilio_settings_to_crm_twilio_settings.py
    │   │       ├── update_deal_quick_entry_layout.py
    │   │       ├── update_deal_status_probabilities.py
    │   │       ├── update_deal_status_type.py
    │   │       └── update_layouts_to_new_format.py
    │   ├── public/
    │   │   ├── .gitkeep
    │   │   └── frontend/
    │   │       ├── index.html
    │   │       ├── manifest.webmanifest
    │   │       ├── registerSW.js
    │   │       ├── sw.js
    │   │       ├── workbox-78e2cf90.js
    │   │       └── assets/
    │   │           ├── ArrowUpRightIcon-6dda4bf5.js
    │   │           ├── AvatarIcon-2e499ef4.js
    │   │           ├── Breadcrumbs.vue_vue_type_script_setup_true_lang-db9aa161.js
    │   │           ├── CalendarIcon-f2e9a1af.js
    │   │           ├── CallLogModal-93ea73ec.css
    │   │           ├── CallLogModal-e5e1b445.js
    │   │           ├── CallLogs-c42143fc.js
    │   │           ├── CameraIcon-49d46078.js
    │   │           ├── CommentIcon-1b2661d2.js
    │   │           ├── Contact-65128319.js
    │   │           ├── ContactModal-bc1ebfc6.css
    │   │           ├── ContactModal-d78a4782.js
    │   │           ├── Contacts-db29d8a8.js
    │   │           ├── ContactsIcon-01c7eddd.js
    │   │           ├── ContactsListView-95d1b097.js
    │   │           ├── CustomActions-5060ff4b.js
    │   │           ├── Deal-efd0dd69.js
    │   │           ├── Deals-49532bdc.js
    │   │           ├── DealsIcon-17e83972.js
    │   │           ├── DealsListView-fcf640af.js
    │   │           ├── DeleteLinkedDocModal-917fe54b.js
    │   │           ├── DetailsIcon-704f8a0f.js
    │   │           ├── Email2Icon-6b6e6a4e.js
    │   │           ├── EmailAtIcon-872d8a0d.js
    │   │           ├── ErrorPage-cfe913ab.js
    │   │           ├── FadedScrollableDiv-010f9d1d.js
    │   │           ├── FieldLayout-343faf7e.js
    │   │           ├── FieldLayout-a0fa8592.css
    │   │           ├── FileUploader-9cf78d39.js
    │   │           ├── FontColor-7e4cc665.js
    │   │           ├── global-648fce17.js
    │   │           ├── GlobalModals-0d7a842b.css
    │   │           ├── helpCenter-667668f2.js
    │   │           ├── Icon-f5b67c07.js
    │   │           ├── IconPicker-69096e46.js
    │   │           ├── IndicatorIcon-fc4954df.js
    │   │           ├── InsertImage-86b9cbb9.js
    │   │           ├── InsertLink-5c035918.js
    │   │           ├── InsertVideo-3c498ccd.js
    │   │           ├── InvalidPage-6cb23ca6.js
    │   │           ├── KanbanView-54491af2.js
    │   │           ├── label-cee0c0db.js
    │   │           ├── LayoutHeader-0269a4d0.js
    │   │           ├── Lead-600a950e.js
    │   │           ├── LeadModal-f78caadc.js
    │   │           ├── Leads-0d4fb612.js
    │   │           ├── LeadsIcon-20dd6bc0.js
    │   │           ├── Link-f0c71ee2.js
    │   │           ├── LinkIcon-284ce2fc.js
    │   │           ├── ListBulkActions-df5201fe.js
    │   │           ├── ListFooter-7c921a2b.js
    │   │           ├── LostReasonModal-16ca50fc.js
    │   │           ├── MarkAsDoneIcon-295dc74d.js
    │   │           ├── MobileContact-67dca2df.js
    │   │           ├── MobileDeal-8e2d2256.js
    │   │           ├── MobileLayout-ddc9f1f2.js
    │   │           ├── MobileLead-1717e2f1.js
    │   │           ├── MobileNotification-a6cd874c.js
    │   │           ├── MobileOrganization-0b145206.js
    │   │           ├── modals-f82a09a6.js
    │   │           ├── MultipleAvatar-dddd7e0f.js
    │   │           ├── NoteModal-1add8c8f.js
    │   │           ├── Notes-21c401f0.js
    │   │           ├── notifications-ee93422c.js
    │   │           ├── Organization-c6aa73f0.js
    │   │           ├── OrganizationModal-c4be8665.js
    │   │           ├── organizations-9ec66051.js
    │   │           ├── Organizations-d17f0258.js
    │   │           ├── OrganizationsIcon-4f7e148c.js
    │   │           ├── PhoneIcon-7100523f.js
    │   │           ├── PinIcon-15b68615.js
    │   │           ├── Popover-39b468f6.js
    │   │           ├── Resizer-138a7577.js
    │   │           ├── sparkpost-3d6653ba.webp
    │   │           ├── statuses-c7bfc148.js
    │   │           ├── Switch.vue_vue_type_script_setup_true_lang-331e5a8f.js
    │   │           ├── TaskIcon-96bdbdea.js
    │   │           ├── TaskModal-8555ebfa.css
    │   │           ├── TaskModal-9eb23770.js
    │   │           ├── Tasks-85271f9b.js
    │   │           ├── useActiveTabManager-7fd4289f.css
    │   │           ├── view-2c80ca05.js
    │   │           ├── view-fa2f0bf9.css
    │   │           ├── ViewBreadcrumbs-82ef4b21.js
    │   │           ├── Welcome-604b22b1.js
    │   │           └── WhatsAppIcon-13be3fbf.js
    │   ├── templates/
    │   │   ├── __init__.py
    │   │   ├── emails/
    │   │   │   ├── crm_invitation.html
    │   │   │   └── helpdesk_invitation.html
    │   │   └── pages/
    │   │       └── __init__.py
    │   ├── utils/
    │   │   └── __init__.py
    │   └── www/
    │       ├── __init__.py
    │       ├── crm.html
    │       └── crm.py
    ├── docs/
    │   ├── AGENTIC_ROADMAP.md
    │   ├── API_INDEX.md
    │   ├── ARCHITECTURE.md
    │   └── ERD.md
    └── .cursor/
        └── rules/
            ├── deployment-doctrine.mdc
            ├── deployment-troubleshooting.mdc
            └── setup-guide.mdc
