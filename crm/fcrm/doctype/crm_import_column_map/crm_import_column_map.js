frappe.ui.form.on('CRM Import Column Map', {
  refresh(frm) {
    if (!frm.doc.title) {
      frm.add_custom_button(__('Save to enable Auto-generate'), () => {}, 'Actions');
      return;
    }

    frm.add_custom_button(__('Auto‑generate Mapping'), () => {
      if (frm.is_new()) {
        frappe.msgprint(__('Please save the document first.'));
        return;
      }

      const d = new frappe.ui.Dialog({
        title: __('Auto‑generate from Source'),
        fields: [
          {
            fieldname: 'source_type',
            label: __('Source Type'),
            fieldtype: 'Select',
            options: ['CSV', 'GOOGLE_SHEETS'],
            default: 'GOOGLE_SHEETS',
            reqd: 1,
          },
          {
            fieldname: 'file_url',
            label: __('CSV File URL'),
            fieldtype: 'Data',
            depends_on: "eval:doc.source_type=='CSV'",
          },
          {
            fieldname: 'sheet_id',
            label: __('Google Sheet ID'),
            fieldtype: 'Data',
            description: __('Use the spreadsheet ID; first sheet is read.'),
            depends_on: "eval:doc.source_type=='GOOGLE_SHEETS'",
          },
        ],
        primary_action_label: __('Generate'),
        primary_action: (values) => {
          if (values.source_type === 'CSV' && !values.file_url) {
            frappe.msgprint(__('Provide CSV File URL'));
            return;
          }
          if (values.source_type === 'GOOGLE_SHEETS' && !values.sheet_id) {
            frappe.msgprint(__('Provide Google Sheet ID'));
            return;
          }

          d.hide();
          frappe.call({
            method: 'crm.api.etl.autogenerate_mapping',
            freeze: true,
            freeze_message: __('Generating mapping…'),
            args: {
              profile_name: frm.doc.title,
              source_type: values.source_type,
              file_url: values.file_url,
              sheet_id: values.sheet_id,
            },
          }).then(() => {
            frm.reload_doc();
            frappe.show_alert({ message: __('Mapping generated'), indicator: 'green' });
          }).catch(() => {
            frappe.msgprint(__('Failed to generate mapping. See Error Log.'));
          });
        },
      });
      d.show();
    }, __('Actions'));
  },
});


