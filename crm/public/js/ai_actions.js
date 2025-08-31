frappe.ui.form.on(cur_frm.doctype, {
	refresh(frm) {
		if (!frm.doc || frm.is_new()) return;
		// Common email target from doc
		const email_target = () => {
			if (frm.doctype === 'CRM Lead') return frm.doc.email_id || '';
			if (frm.doctype === 'Contact') return (frm.doc.email_id || (frm.doc.email_ids && frm.doc.email_ids[0] && frm.doc.email_ids[0].email_id)) || '';
			return '';
		};

		frm.add_custom_button('AI Triage Thread', () => {
			frappe.prompt([
				{ fieldname: 'communication', label: 'Communication Name', fieldtype: 'Link', options: 'Communication', reqd: 1 }
			], (v) => {
				frappe.call({
					method: 'crm.api.agent.run',
					args: { command: 'email.triage', params: { communication_name: v.communication } },
					callback: (r) => {
						if (r.message) {
							frappe.msgprint({ title: 'AI Triage', message: `<pre>${JSON.stringify(r.message, null, 2)}</pre>` });
						}
					}
				});
			});
		}, 'AI');

		frm.add_custom_button('AI Draft Reply', () => {
			const to = email_target();
			frappe.prompt([
				{ fieldname: 'to', label: 'To', fieldtype: 'Data', default: to, reqd: 1 },
				{ fieldname: 'subject', label: 'Subject', fieldtype: 'Data', reqd: 1 },
				{ fieldname: 'body', label: 'Body (HTML)', fieldtype: 'Small Text', reqd: 1 },
			], (v) => {
				frappe.call({
					method: 'crm.api.agent.run',
					args: {
						command: 'email.draft',
						params: {
							reference_doctype: frm.doctype,
							reference_name: frm.doc.name,
							to: v.to,
							subject: v.subject,
							html: v.body
						}
					}
				}).then((r) => {
					const name = r.message;
					frappe.msgprint(`Draft created: <a href="/app/communication/${name}" target="_blank">${name}</a>`);
				});
			});
		}, 'AI');

		frm.add_custom_button('Send Email', () => {
			frappe.prompt([
				{ fieldname: 'communication', label: 'Communication Name', fieldtype: 'Link', options: 'Communication', reqd: 1 }
			], (v) => {
				frappe.call({
					method: 'crm.api.agent.run',
					args: { command: 'email.send', params: { communication_name: v.communication } },
					callback: (r) => {
						if (r.message && r.message.ok) {
							frappe.show_alert('Email sent!', 'success');
						}
					}
				});
			});
		}, 'AI');
	}
});
