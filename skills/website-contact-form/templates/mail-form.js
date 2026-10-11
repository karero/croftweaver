// The mail-app contact form (the website-contact-form skill), installed as
// public/js/mail-form.js and loaded by src/components/MailForm.astro. A file of the
// site's own, not an inline script, so a strict Content-Security-Policy
// (script-src 'self') lets it run. Plain JavaScript: it is served exactly as written.
//
// It shows the form (hidden without JavaScript, where it could do nothing), and on
// the button builds a mailto: link from the fields and opens it. Nothing leaves the
// visitor's browser except through their own email program.
(function () {
  'use strict';

  document.querySelectorAll('form[data-mail-form]').forEach(function (form) {
    var status = form.querySelector('[data-mail-form-status]');
    form.hidden = false;

    form.addEventListener('submit', function (event) {
      // The browser has already checked the required fields: an empty one stops it
      // before this runs.
      event.preventDefault();

      // `required` lets a field of spaces through; the mail would arrive without it.
      // Emptied, the browser stops it the way it stops an empty one.
      Array.prototype.forEach.call(form.elements, function (field) {
        if (field.required && typeof field.value === 'string' && !field.value.trim()) field.value = '';
      });
      if (!form.reportValidity()) return;

      // Said before anything else: whether the mail program opened, and whether the
      // visitor pressed Send there, the site never learns. The line also points to the
      // address under the form, for when nothing opens.
      if (status) status.textContent = status.dataset.opened;

      // The address, decoded as EmailLink decodes it (src/lib/obfuscate.ts).
      var to;
      try {
        // A % in the address is the one character the starter's encoding allows that a
        // mailto: link must escape.
        to = atob(form.dataset.to).split('').reverse().join('').replace(/%/g, '%25');
      } catch (e) {
        console.error('mail form: the address could not be decoded', e);
        return;
      }

      // The message is the mail, as typed, less any empty space (spaces, tabs, blank
      // lines) at its very start and end: the visitor writes their own greeting and
      // sign-off, and their mail program adds who they are. Every other field the visitor
      // filled in follows under it as "Label: value", so a field the owner adds later is
      // sent too: a list gives every chosen entry, a ticked checkbox or radio button its
      // label alone.
      var details = [];
      Array.prototype.forEach.call(form.elements, function (field) {
        // A named <fieldset> or <output> has no value of its own to send.
        if (!field.name || field.name === 'message' || field.type === 'submit' || field.type === 'button' || typeof field.value !== 'string') return;
        var label = field.labels && field.labels[0] ? field.labels[0].textContent.trim() : field.name;
        if (field.type === 'checkbox' || field.type === 'radio') {
          if (field.checked) details.push(label);
          return;
        }
        var value = field.tagName === 'SELECT'
          ? Array.prototype.map.call(field.selectedOptions, function (option) { return option.text.trim(); }).join(', ')
          : field.value.trim();
        if (value) details.push(label + ': ' + value);
      });
      var message = form.elements.message ? form.elements.message.value.trim() : '';
      var lines = [message];
      if (details.length) lines.push('', details.join('\n'));
      var body = lines.join('\n');

      // RFC 6068: a line break in a mailto: body is %0D%0A. A broken character pasted
      // into a field (half of an emoji) makes encoding throw; the status line already
      // points to the address below.
      var href;
      try {
        href = 'mailto:' + to
          + '?subject=' + encodeURIComponent(form.dataset.subject)
          + '&body=' + encodeURIComponent(body.replace(/\r?\n/g, '\r\n'));
      } catch (e) {
        console.error('mail form: the message could not be put into a link', e);
        return;
      }

      window.location.href = href;
    });
  });
})();
