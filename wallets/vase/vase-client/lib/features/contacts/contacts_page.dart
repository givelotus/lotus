import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:vase/features/send/send_model.dart';
import 'contacts_model.dart';
import 'device_contacts.dart';

class ContactsPage extends StatefulWidget {
  const ContactsPage({
    super.key,
    this.onBack,
    this.model,
    this.deviceContacts = const DeviceContacts(),
  });
  final VoidCallback? onBack;
  final ContactsModel? model;
  final DeviceContacts deviceContacts;
  @override
  State<ContactsPage> createState() => _ContactsPageState();
}

class _ContactsPageState extends State<ContactsPage> {
  late final ContactsModel _model = widget.model ?? ContactsModel();
  String _query = '';
  bool _deviceBusy = false;
  @override
  void initState() {
    super.initState();
    _model.load();
  }

  @override
  void dispose() {
    if (widget.model == null) _model.dispose();
    super.dispose();
  }

  void _message(String text) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
    }
  }

  Future<void> _edit({WalletContact? contact, DeviceContactLink? link}) async {
    await showDialog<void>(
      context: context,
      builder: (_) =>
          _ContactEditor(model: _model, contact: contact, link: link),
    );
  }

  Future<void> _pick({WalletContact? contact}) async {
    setState(() => _deviceBusy = true);
    try {
      final link = await widget.deviceContacts.pick();
      if (mounted && link != null) await _edit(contact: contact, link: link);
    } catch (_) {
      _message('Unable to open phone contacts');
    } finally {
      if (mounted) setState(() => _deviceBusy = false);
    }
  }

  Future<void> _delete(WalletContact contact) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Remove ${contact.name}?'),
        content: const Text(
          'This removes the Vase contact only. Your phone contact is kept.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await _model.remove(contact.id);
    } catch (_) {
      _message('Unable to save contacts');
    }
  }

  Future<void> _writePhone(WalletContact contact) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Save address to phone contact?'),
        content: Text(
          'Add a website field labelled Lotus XPI to the linked phone contact for ${contact.name}:\n\n${contact.address}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Save address'),
          ),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    setState(() => _deviceBusy = true);
    try {
      await widget.deviceContacts.writeAddress(contact);
      _message('Address saved to phone contact');
    } catch (_) {
      _message(
        'Unable to update phone contact. Check its availability and contacts permission.',
      );
    } finally {
      if (mounted) setState(() => _deviceBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _model,
    builder: (context, _) {
      final records = _model.contacts
          .where(
            (c) =>
                c.name.toLowerCase().contains(_query.toLowerCase()) ||
                c.address.contains(_query),
          )
          .toList();
      final enabled =
          _model.loaded && !_model.unavailable && !_model.busy && !_deviceBusy;
      return Scaffold(
        appBar: AppBar(
          title: const Text('Contacts'),
          leading: IconButton(
            tooltip: 'Back to scanner',
            icon: const Icon(Icons.navigate_before),
            onPressed: widget.onBack ?? () => context.pop(),
          ),
          actions: [
            if (widget.deviceContacts.supported)
              IconButton(
                tooltip: 'Import phone contact',
                icon: const Icon(Icons.contact_phone),
                onPressed: enabled ? () => _pick() : null,
              ),
            IconButton(
              tooltip: 'Add contact',
              icon: const Icon(Icons.person_add),
              onPressed: enabled ? () => _edit() : null,
            ),
          ],
        ),
        body: _model.unavailable
            ? Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('Contacts unavailable'),
                    const Text('Your saved contacts have been kept.'),
                    TextButton(
                      onPressed: () => _model.load(),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              )
            : !_model.loaded
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: TextField(
                      onChanged: (value) => setState(() => _query = value),
                      decoration: const InputDecoration(
                        labelText: 'Search contacts',
                        prefixIcon: Icon(Icons.search),
                      ),
                    ),
                  ),
                  Expanded(
                    child: records.isEmpty
                        ? Center(
                            child: Text(
                              _query.isEmpty
                                  ? 'Add someone to pay by name'
                                  : 'No matching contacts',
                            ),
                          )
                        : ListView.builder(
                            itemCount: records.length,
                            itemBuilder: (context, index) {
                              final contact = records[index];
                              return ListTile(
                                title: Text(contact.name),
                                subtitle: Text(
                                  contact.address,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                leading: const CircleAvatar(
                                  child: Icon(Icons.person),
                                ),
                                onTap: enabled
                                    ? () async {
                                        context.read<SendModel>().setPayment(
                                          contact.address,
                                          BigInt.zero,
                                        );
                                        await context.push('/send');
                                      }
                                    : null,
                                trailing: PopupMenuButton<String>(
                                  enabled: enabled,
                                  tooltip: 'Contact actions',
                                  onSelected: (action) async {
                                    switch (action) {
                                      case 'edit':
                                        await _edit(contact: contact);
                                      case 'copy':
                                        await Clipboard.setData(
                                          ClipboardData(text: contact.address),
                                        );
                                        _message('Address copied');
                                      case 'link':
                                        await _pick(contact: contact);
                                      case 'phone':
                                        await _writePhone(contact);
                                      case 'delete':
                                        await _delete(contact);
                                    }
                                  },
                                  itemBuilder: (_) => [
                                    const PopupMenuItem(
                                      value: 'edit',
                                      child: Text('Edit'),
                                    ),
                                    const PopupMenuItem(
                                      value: 'copy',
                                      child: Text('Copy address'),
                                    ),
                                    if (widget.deviceContacts.supported)
                                      const PopupMenuItem(
                                        value: 'link',
                                        child: Text('Link phone contact'),
                                      ),
                                    if (widget.deviceContacts.supported &&
                                        contact.deviceContactId != null)
                                      const PopupMenuItem(
                                        value: 'phone',
                                        child: Text(
                                          'Save address to phone contact',
                                        ),
                                      ),
                                    const PopupMenuItem(
                                      value: 'delete',
                                      child: Text('Remove'),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                  ),
                ],
              ),
      );
    },
  );
}

class _ContactEditor extends StatefulWidget {
  const _ContactEditor({required this.model, this.contact, this.link});
  final ContactsModel model;
  final WalletContact? contact;
  final DeviceContactLink? link;
  @override
  State<_ContactEditor> createState() => _ContactEditorState();
}

class _ContactEditorState extends State<_ContactEditor> {
  late final _name = TextEditingController(
    text: widget.contact?.name ?? widget.link?.name,
  );
  late final _address = TextEditingController(
    text: widget.contact?.address ?? widget.link?.address,
  );
  bool _saving = false;
  String? _error;
  @override
  void dispose() {
    _name.dispose();
    _address.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    try {
      if (_name.text.trim().isEmpty) throw const FormatException();
      contactAddress(_address.text);
    } catch (_) {
      setState(() => _error = 'Enter a name and valid Lotus mainnet address');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.model.save(
        id: widget.contact?.id,
        name: _name.text,
        address: _address.text,
        deviceContactId: widget.link?.id ?? widget.contact?.deviceContactId,
      );
      if (mounted) Navigator.pop(context);
    } catch (_) {
      if (mounted) {
        setState(
          () =>
              _error = 'Unable to save. Your existing contacts have been kept.',
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(widget.contact == null ? 'Add contact' : 'Edit contact'),
    content: SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _name,
            enabled: !_saving,
            maxLength: 120,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(labelText: 'Name'),
          ),
          TextField(
            controller: _address,
            enabled: !_saving,
            maxLines: 3,
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(
              labelText: 'Lotus address',
              hintText: 'lotus_…',
            ),
          ),
          if (widget.link != null || widget.contact?.deviceContactId != null)
            const Text(
              'Linked to a phone contact. Saving here does not change your phone contact.',
            ),
          if (_error != null)
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: _saving ? null : () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      TextButton(
        onPressed: _saving ? null : _save,
        child: Text(_saving ? 'Saving…' : 'Save'),
      ),
    ],
  );
}
