import 'dart:async';
import 'package:flutter_contacts/flutter_contacts.dart' show PermissionStatus;
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
    this.active = true,
    this.model,
    this.deviceContacts = const DeviceContacts(),
  });
  final bool active;
  final VoidCallback? onBack;
  final ContactsModel? model;
  final DeviceContacts deviceContacts;
  @override
  State<ContactsPage> createState() => _ContactsPageState();
}

class _ContactsPageState extends State<ContactsPage>
    with WidgetsBindingObserver {
  late final ContactsModel _model = widget.model ?? ContactsModel();
  String _query = '';
  bool _deviceBusy = false;
  List<DeviceContactLink> _phoneContacts = [];
  PermissionStatus? _permission;
  String? _syncError;
  bool _syncing = false, _syncAgain = false, _permissionAttempted = false;
  StreamSubscription<void>? _changes;

  Future<void> _sync() async {
    if (!mounted || !widget.active || !widget.deviceContacts.supported) return;
    if (_syncing) {
      _syncAgain = true;
      return;
    }
    setState(() => _syncing = true);
    try {
      do {
        _syncAgain = false;
        final request = !_permissionAttempted;
        _permissionAttempted = true;
        final snapshot = await widget.deviceContacts.read(
          requestPermission: request,
        );
        if (!mounted) return;
        setState(() {
          _permission = snapshot.status;
          _phoneContacts = snapshot.contacts;
          _syncError = null;
        });
      } while (_syncAgain && widget.active);
    } catch (_) {
      if (mounted) {
        setState(() => _syncError = 'Phone contacts could not refresh.');
      }
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _sync();
  }

  @override
  void didUpdateWidget(ContactsPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !oldWidget.active) _sync();
  }

  @override
  void initState() {
    super.initState();
    _model.load();
    WidgetsBinding.instance.addObserver(this);
    if (widget.deviceContacts.supported) {
      _changes = widget.deviceContacts.changes.listen(
        (_) => _sync(),
        onError: (Object _) {
          if (mounted) {
            setState(() => _syncError = 'Phone contacts could not refresh.');
          }
        },
      );
      WidgetsBinding.instance.addPostFrameCallback((_) => _sync());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _changes?.cancel();
    if (widget.model == null) _model.dispose();
    super.dispose();
  }

  void _message(String text) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
    }
  }

  Future<void> _edit({WalletContact? contact, DeviceContactLink? link}) async {
    final phoneUpdate = await showDialog<WalletContact>(
      context: context,
      builder: (_) => _ContactEditor(
        model: _model,
        contact: contact,
        link: link,
        canWritePhone: widget.deviceContacts.supported,
      ),
    );
    if (phoneUpdate != null && mounted) await _writePhone(phoneUpdate);
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
          'Save this address in the Lotus XPI website field of the linked phone contact for ${contact.name}? Existing Lotus XPI fields will be replaced. Other fields, including the phone contact name, are kept. Your Vase copy is already saved.\n\nAddress:\n\n${contact.address}',
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
      final savedByPhone = <String, WalletContact>{};
      for (final contact in _model.contacts) {
        if (contact.deviceContactId != null) {
          savedByPhone.putIfAbsent(contact.deviceContactId!, () => contact);
        }
      }
      final phoneRecords =
          _phoneContacts
              .where(
                (c) =>
                    c.name.toLowerCase().contains(_query.toLowerCase()) ||
                    (c.address?.contains(_query) ?? false) ||
                    (savedByPhone[c.id]?.address.contains(_query) ?? false),
              )
              .toList()
            ..sort(
              (a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()),
            );
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
                  if (widget.deviceContacts.supported)
                    ListTile(
                      dense: true,
                      title: Text(
                        _syncError ??
                            (_permission == PermissionStatus.limited
                                ? 'Showing selected phone contacts'
                                : _permission == PermissionStatus.granted
                                ? 'Phone contacts synced'
                                : _syncing
                                ? 'Loading phone contacts…'
                                : 'Allow Contacts access in Settings to sync your phone contacts'),
                      ),
                      trailing: _syncing
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : IconButton(
                              tooltip:
                                  _syncError != null ||
                                      _permission == PermissionStatus.granted
                                  ? 'Refresh phone contacts'
                                  : 'Manage contacts access',
                              icon: Icon(
                                _syncError != null ||
                                        _permission == PermissionStatus.granted
                                    ? Icons.refresh
                                    : Icons.settings,
                              ),
                              onPressed: () async {
                                if (_syncError != null ||
                                    _permission == PermissionStatus.granted) {
                                  await _sync();
                                } else {
                                  try {
                                    await widget.deviceContacts.openSettings();
                                  } catch (_) {
                                    _message(
                                      'Unable to open contacts settings',
                                    );
                                  }
                                }
                              },
                            ),
                    ),
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
                    child: records.isEmpty && phoneRecords.isEmpty
                        ? Center(
                            child: Text(
                              _query.isEmpty
                                  ? 'Add someone to pay by name'
                                  : 'No matching contacts',
                            ),
                          )
                        : ListView.builder(
                            itemCount:
                                records.length +
                                phoneRecords.length +
                                (records.isEmpty ? 0 : 1) +
                                (phoneRecords.isEmpty ? 0 : 1),
                            itemBuilder: (context, index) {
                              if (records.isNotEmpty) {
                                if (index == 0)
                                  return const ListTile(
                                    dense: true,
                                    title: Text('Saved in Vase'),
                                  );
                                index--;
                              }
                              if (index >= records.length) {
                                final phoneIndex = index - records.length;
                                if (phoneIndex == 0)
                                  return const ListTile(
                                    dense: true,
                                    title: Text('Phone contacts'),
                                  );
                                final phone = phoneRecords[phoneIndex - 1];
                                final saved = savedByPhone[phone.id];
                                final address = phone.address ?? saved?.address;
                                return ListTile(
                                  leading: const CircleAvatar(
                                    child: Icon(Icons.person_outline),
                                  ),
                                  title: Text(
                                    phone.name.isEmpty
                                        ? 'Unnamed contact'
                                        : phone.name,
                                  ),
                                  subtitle: Text(
                                    address ?? 'Add Lotus address',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  onTap: enabled
                                      ? () async {
                                          if (address == null) {
                                            await _edit(
                                              contact: saved,
                                              link: phone,
                                            );
                                          } else {
                                            context
                                                .read<SendModel>()
                                                .setPayment(
                                                  address,
                                                  BigInt.zero,
                                                );
                                            await context.push('/send');
                                          }
                                        }
                                      : null,
                                  trailing: IconButton(
                                    tooltip: saved == null
                                        ? 'Save in Vase'
                                        : 'Edit saved contact',
                                    icon: const Icon(Icons.person_add_alt),
                                    onPressed: enabled
                                        ? () =>
                                              _edit(contact: saved, link: phone)
                                        : null,
                                  ),
                                );
                              }
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
  const _ContactEditor({
    required this.model,
    this.contact,
    this.link,
    required this.canWritePhone,
  });
  final bool canWritePhone;
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
  final _addressFocus = FocusNode();
  bool _saving = false;
  bool _saveToPhone = false;
  String? _error;
  @override
  void dispose() {
    _name.dispose();
    _address.dispose();
    _addressFocus.dispose();
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
      if (mounted)
        Navigator.pop(
          context,
          _saveToPhone
              ? WalletContact(
                  id: widget.contact?.id ?? 'phone-update',
                  name: _name.text.trim(),
                  address: contactAddress(_address.text),
                  deviceContactId:
                      widget.link?.id ?? widget.contact?.deviceContactId,
                )
              : null,
        );
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
            autofocus: true,
            maxLength: 120,
            textInputAction: TextInputAction.next,
            onSubmitted: (_) => _addressFocus.requestFocus(),
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Name',
              border: OutlineInputBorder(),
              counterText: '',
              isDense: true,
            ),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _address,
            focusNode: _addressFocus,
            enabled: !_saving,
            maxLines: 1,
            keyboardType: TextInputType.url,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _save(),
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(
              labelText: 'Lotus address',
              hintText: 'lotus_…',
              border: OutlineInputBorder(),
              isDense: true,
            ),
          ),
          if (widget.canWritePhone &&
              (widget.link != null || widget.contact?.deviceContactId != null))
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _saveToPhone,
              onChanged: _saving
                  ? null
                  : (value) => setState(() => _saveToPhone = value!),
              title: const Text('Also update phone contact'),
              subtitle: const Text(
                'Save the Lotus address after confirmation. The name above is used only in Vase.',
              ),
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
