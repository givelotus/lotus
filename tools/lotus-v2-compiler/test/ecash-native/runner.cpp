// Copyright (c) 2026 The Lotus developers
// Actual pinned ABC interpreter; restricted direct-locking-script test adapter.
#include <array>
#include <iostream>
#include <policy/policy.h>
#include <script/interpreter.h>
#include <script/script_error.h>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr uint32_t FLAGS =
    STANDARD_SCRIPT_VERIFY_FLAGS | SCRIPT_VERIFY_MINIMALIF;
constexpr const char *REVISION = "1fb7db17c176cdea8a2c60d887891589382ee4e3";
constexpr const char *TREE = "b2e4a0a9f57c593129028352d5dbb0c4ff294cdb";
struct Flag {
  const char *name;
  uint32_t mask;
};
constexpr std::array FLAG_NAMES{
    Flag{"SCRIPT_VERIFY_P2SH", SCRIPT_VERIFY_P2SH},
    Flag{"SCRIPT_VERIFY_STRICTENC", SCRIPT_VERIFY_STRICTENC},
    Flag{"SCRIPT_VERIFY_DERSIG", SCRIPT_VERIFY_DERSIG},
    Flag{"SCRIPT_VERIFY_LOW_S", SCRIPT_VERIFY_LOW_S},
    Flag{"SCRIPT_VERIFY_SIGPUSHONLY", SCRIPT_VERIFY_SIGPUSHONLY},
    Flag{"SCRIPT_VERIFY_MINIMALDATA", SCRIPT_VERIFY_MINIMALDATA},
    Flag{"SCRIPT_VERIFY_DISCOURAGE_UPGRADABLE_NOPS",
         SCRIPT_VERIFY_DISCOURAGE_UPGRADABLE_NOPS},
    Flag{"SCRIPT_VERIFY_CLEANSTACK", SCRIPT_VERIFY_CLEANSTACK},
    Flag{"SCRIPT_VERIFY_CHECKLOCKTIMEVERIFY",
         SCRIPT_VERIFY_CHECKLOCKTIMEVERIFY},
    Flag{"SCRIPT_VERIFY_CHECKSEQUENCEVERIFY",
         SCRIPT_VERIFY_CHECKSEQUENCEVERIFY},
    Flag{"SCRIPT_VERIFY_MINIMALIF", SCRIPT_VERIFY_MINIMALIF},
    Flag{"SCRIPT_VERIFY_NULLFAIL", SCRIPT_VERIFY_NULLFAIL},
    Flag{"SCRIPT_ENABLE_SIGHASH_FORKID", SCRIPT_ENABLE_SIGHASH_FORKID},
    Flag{"SCRIPT_DISALLOW_SEGWIT_RECOVERY", SCRIPT_DISALLOW_SEGWIT_RECOVERY},
    Flag{"SCRIPT_ENABLE_SCHNORR_MULTISIG", SCRIPT_ENABLE_SCHNORR_MULTISIG},
    Flag{"SCRIPT_VERIFY_INPUT_SIGCHECKS", SCRIPT_VERIFY_INPUT_SIGCHECKS},
    Flag{"SCRIPT_ENFORCE_SIGCHECKS", SCRIPT_ENFORCE_SIGCHECKS}};
std::string Json(const std::string &value) {
  std::string out = "\"";
  const char *hex = "0123456789abcdef";
  for (unsigned char c : value) {
    if (c == '\\' || c == '"') {
      out += '\\';
      out += c;
    } else if (c < 32) {
      out += "\\u00";
      out += hex[c >> 4];
      out += hex[c & 15];
    } else
      out += c;
  }
  return out + '"';
}
std::vector<uint8_t> Bytes(const char *argument) {
  const std::string text(argument);
  if (text.size() % 2 || text.size() > (2 << 20))
    throw std::runtime_error("invalid hex width or local argument capacity");
  auto digit = [](char c) -> unsigned {
    if (c >= '0' && c <= '9')
      return c - '0';
    if (c >= 'a' && c <= 'f')
      return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
      return c - 'A' + 10;
    throw std::runtime_error("invalid hex character");
  };
  std::vector<uint8_t> out;
  for (size_t i = 0; i < text.size(); i += 2)
    out.push_back((digit(text[i]) << 4) | digit(text[i + 1]));
  return out;
}
template <class T> std::string Hex(const T &bytes) {
  const char *hex = "0123456789abcdef";
  std::string out;
  for (uint8_t byte : bytes) {
    out += hex[byte >> 4];
    out += hex[byte & 15];
  }
  return out;
}
void PushCanonical(CScript &script, const std::vector<uint8_t> &bytes) {
  if (bytes.empty())
    script << OP_0;
  else if (bytes.size() == 1 && bytes[0] >= 1 && bytes[0] <= 16)
    script << opcodetype(OP_1 + bytes[0] - 1);
  else if (bytes.size() == 1 && bytes[0] == 0x81)
    script << OP_1NEGATE;
  else
    script << bytes;
}
std::string Unsupported(const CScript &script) {
  if (script.IsPayToScriptHash())
    return "P2SH envelope is outside the direct locking script profile";
  for (auto cursor = script.begin(); cursor != script.end();) {
    opcodetype opcode;
    std::vector<uint8_t> pushed;
    if (!script.GetOp(cursor, opcode, pushed))
      return {}; // Native BAD_OPCODE owns malformed framing.
    switch (opcode) {
    case OP_CHECKSIG:
    case OP_CHECKSIGVERIFY:
    case OP_CHECKMULTISIG:
    case OP_CHECKMULTISIGVERIFY:
    case OP_CHECKDATASIG:
    case OP_CHECKDATASIGVERIFY:
    case OP_CODESEPARATOR:
    case OP_CHECKLOCKTIMEVERIFY:
    case OP_CHECKSEQUENCEVERIFY:
      return "signature or transaction context is unsupported";
    case OP_RESERVED1:
    case OP_RESERVED2:
      return "reserved 0x89/0x8a extensions are unsupported; no V2 instruction "
             "semantics";
    default:
      break;
    }
  }
  return {};
}
void Report(const char *status, bool accepted, bool executed,
            const std::vector<std::vector<uint8_t>> &stack,
            const std::string &error, int error_code,
            const std::string &evaluation_error, const CScript &script_sig) {
  std::cout << "{\"schema\":\"ecash-native-script/1\",\"status\":"
            << Json(status) << ",\"accepted\":" << (accepted ? "true" : "false")
            << ",\"executed\":" << (executed ? "true" : "false")
            << ",\"final_stack\":[";
  for (size_t i = 0; i < stack.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << Json(Hex(stack[i]));
  }
  std::cout << "],\"error\":" << Json(error) << ",\"error_code\":" << error_code
            << ",\"evaluation_error\":" << Json(evaluation_error)
            << ",\"script_sig\":" << Json(Hex(script_sig))
            << ",\"revision\":" << Json(REVISION) << ",\"tree\":" << Json(TREE)
            << ",\"verification_profile\":\"ecash-script-minimal-cleanstack-"
               "1fb7db17\""
            << ",\"targetProfile\":\"ecash-script-minimal-cleanstack-1fb7db17\""
            << ",\"flags_mask\":" << FLAGS << ",\"flags\":[";
  bool first = true;
  for (const auto &flag : FLAG_NAMES)
    if (FLAGS & flag.mask) {
      if (!first)
        std::cout << ',';
      first = false;
      std::cout << Json(flag.name);
    }
  std::cout << "],\"interpreter_sha256\":" << Json(ECASH_INTERPRETER_SHA256)
            << ",\"script_flags_sha256\":" << Json(ECASH_FLAGS_SHA256)
            << ",\"policy_sha256\":" << Json(ECASH_POLICY_SHA256) << "}\n";
}
} // namespace

int main(int argc, char **argv) {
  try {
    if (argc == 2 && std::string(argv[1]) == "--describe") {
      Report("descriptor", false, false, {}, "", -1, "", {});
      return 0;
    }
    if (argc < 2 || argc > 4098)
      throw std::runtime_error("usage: ecash-native SCRIPT_HEX ARG_HEX...; "
                               "arguments are bottom-to-top");
    const auto raw = Bytes(argv[1]);
    const CScript script(raw.begin(), raw.end());
    CScript script_sig;
    size_t total = raw.size();
    for (int i = 2; i < argc; ++i) {
      const auto value = Bytes(argv[i]);
      total += value.size();
      if (total > (2 << 20))
        throw std::runtime_error("local total argument capacity exceeded");
      PushCanonical(script_sig, value);
    }
    const auto unsupported = Unsupported(script);
    if (!unsupported.empty()) {
      Report("unsupported", false, false, {}, unsupported, -1, "", script_sig);
      return 0;
    }
    const BaseSignatureChecker checker;
    ScriptError verify_error = ScriptError::UNKNOWN,
                eval_error = ScriptError::UNKNOWN;
    // VerifyScript is the sole acceptance decision. Replay its two native
    // EvalScript calls to expose final/partial stack for this direct profile.
    const bool accepted =
        VerifyScript(script_sig, script, FLAGS, checker, &verify_error);
    std::vector<std::vector<uint8_t>> stack;
    ScriptExecutionMetrics metrics;
    bool evaluated =
        EvalScript(stack, script_sig, FLAGS, checker, metrics, &eval_error);
    if (evaluated)
      evaluated =
          EvalScript(stack, script, FLAGS, checker, metrics, &eval_error);
    if (accepted &&
        (!evaluated || stack.size() != 1 || !CastToBool(stack.back())))
      throw std::runtime_error(
          "native VerifyScript/EvalScript result discrepancy");
    Report(accepted ? "accepted" : "rejected", accepted, true, stack,
           ScriptErrorString(verify_error), int(verify_error),
           ScriptErrorString(eval_error), script_sig);
    return 0;
  } catch (const std::exception &error) {
    Report("malformed_input", false, false, {}, error.what(), -1, "", {});
    return 1;
  }
}
