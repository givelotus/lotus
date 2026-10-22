// Benchmark-only adapters. No production RPC path is changed.
#include <univalue.h>
#include "simdjson.h"
#include "yyjson.h"
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

static std::string_view Trim(std::string_view x) {
    while (!x.empty() && (x.back()==' ' || x.back()=='\t' || x.back()=='\n' || x.back()=='\r')) x.remove_suffix(1);
    return x;
}
// Preserve arbitrary-size integer/exponent lexemes without a floating conversion.
static bool Number(std::string_view x) {
    size_t i=0; if (i<x.size() && x[i]=='-') ++i;
    if (i==x.size()) return false;
    if (x[i]=='0') ++i;
    else { if (x[i]<'1'||x[i]>'9') return false; do {++i;} while(i<x.size()&&x[i]>='0'&&x[i]<='9'); }
    if(i<x.size()&&x[i]=='.') {++i;size_t p=i;while(i<x.size()&&x[i]>='0'&&x[i]<='9')++i;if(i==p)return false;}
    if(i<x.size()&&(x[i]=='e'||x[i]=='E')) {++i;if(i<x.size()&&(x[i]=='+'||x[i]=='-'))++i;size_t p=i;while(i<x.size()&&x[i]>='0'&&x[i]<='9')++i;if(i==p)return false;}
    return i==x.size();
}
static UniValue FromSimd(simdjson::ondemand::value x, size_t depth=0) {
    using simdjson::ondemand::json_type;
    const auto type=x.type().value();
    if ((type==json_type::array || type==json_type::object) && depth>=512) throw std::runtime_error("depth");
    switch(type) {
    case json_type::array: {
        UniValue out(UniValue::VARR);
        for(auto child:x.get_array())out.push_back(FromSimd(child.value(),depth+1));
        return out;
    }
    case json_type::object: {
        UniValue out(UniValue::VOBJ);
        for(auto item:x.get_object()) {
            auto field=item.value();
            std::string key(field.unescaped_key().value());
            out.pushKVEnd(std::move(key),FromSimd(field.value(),depth+1));
        }
        return out;
    }
    case json_type::string:return UniValue(std::string(x.get_string().value()));
    case json_type::number: {
        auto raw=Trim(x.raw_json_token());
        if(!Number(raw))throw std::runtime_error("number");
        return UniValue(UniValue::VNUM,std::string(raw));
    }
    case json_type::boolean:return UniValue(x.get_bool().value());
    case json_type::null:if(!x.is_null().value())throw std::runtime_error("null");return UniValue();
    }
    throw std::runtime_error("type");
}
static UniValue FromYy(yyjson_val* x,size_t depth=0) {
    if ((yyjson_is_arr(x)||yyjson_is_obj(x)) && depth>=512) throw std::runtime_error("depth");
    if(yyjson_is_raw(x))return UniValue(UniValue::VNUM,std::string(yyjson_get_raw(x),yyjson_get_len(x)));
    if(yyjson_is_str(x))return UniValue(std::string(yyjson_get_str(x),yyjson_get_len(x)));
    if(yyjson_is_bool(x))return UniValue(yyjson_get_bool(x));
    if(yyjson_is_null(x))return UniValue();
    if(yyjson_is_arr(x)) {
        UniValue out(UniValue::VARR);out.reserve(yyjson_arr_size(x));
        size_t idx,max;yyjson_val* val;
        yyjson_arr_foreach(x,idx,max,val)out.push_back(FromYy(val,depth+1));
        return out;
    }
    if(yyjson_is_obj(x)) {
        UniValue out(UniValue::VOBJ);out.reserve(yyjson_obj_size(x));
        size_t idx,max;yyjson_val *key,*val;
        yyjson_obj_foreach(x,idx,max,key,val)out.pushKVEnd(std::string(yyjson_get_str(key),yyjson_get_len(key)),FromYy(val,depth+1));
        return out;
    }
    throw std::runtime_error("yy type");
}
struct Parsers {
    simdjson::ondemand::parser simd;
    UniValue Parse(int which,const std::string& input) {
        if(which==0) { UniValue out;if(!out.read(input))throw std::runtime_error("UniValue parse");return out; }
        if(which==1) {
            // A root wrapper permits arbitrary exact scalar-number lexemes too.
            // Its copy/padding/allocation cost is INCLUDED in every measurement.
            simdjson::padded_string owned("["+input+"]");
            auto doc=simd.iterate(owned).value();
            UniValue out;size_t count=0;
            for(auto child:doc.get_array()) {out=FromSimd(child.value());++count;}
            if(count!=1 || !doc.at_end())throw std::runtime_error("trailing input");
            return out; // All strings/keys/number tokens are owned before parser/input die.
        }
        yyjson_read_err err{};
        std::unique_ptr<yyjson_doc,decltype(&yyjson_doc_free)> doc(yyjson_read_opts(const_cast<char*>(input.data()),input.size(),YYJSON_READ_NUMBER_AS_RAW,nullptr,&err),&yyjson_doc_free);
        if(!doc)throw std::runtime_error("yyjson parse");
        return FromYy(yyjson_doc_get_root(doc.get()));
    }
};
static std::string Load(const std::string& f) {std::ifstream in(f,std::ios::binary);if(!in)throw std::runtime_error(f);return {std::istreambuf_iterator<char>(in),{}};}
int main(int argc,char**argv) {
    if(argc<3)throw std::runtime_error("usage parser_bench check|bench corpus-dir [seconds]");
    std::string dir=argv[2];Parsers parsers;
    if(std::string(argv[1])=="check") {
        UniValue tests; if(!tests.read(Load(dir+"/correctness.json")))throw std::runtime_error("corpus");
        size_t mismatches=0;
        for(const auto& row:tests.getValues()) {
            std::string hex=row["input_hex"].get_str(),text;for(size_t i=0;i<hex.size();i+=2)text.push_back(char(std::stoul(hex.substr(i,2),nullptr,16)));bool accepted[3]{};std::string outputs[3];
            for(int p=0;p<3;++p)try {auto value=parsers.Parse(p,text);outputs[p]=value.write();accepted[p]=true;}catch(const std::exception&){}
            for(int p=1;p<3;++p)if(accepted[p]!=accepted[0]||(accepted[p]&&outputs[p]!=outputs[0]))++mismatches;
            std::cout<<row["name"].write()<<'\t'<<accepted[0]<<'\t'<<accepted[1]<<'\t'<<accepted[2]<<'\t'<<(accepted[1]&&outputs[1]==outputs[0])<<'\t'<<(accepted[2]&&outputs[2]==outputs[0])<<'\n';
        }
        // Reuse parser and overwrite input before inspecting a retained tree.
        for(int p=0;p<3;++p) {
            auto retained=parsers.Parse(p,"{\"a\":[\"first\",9007199254740993,1.2300e-2]}");
            auto expected=retained.write();for(int i=0;i<32;++i)(void)parsers.Parse(p,"[\"overwrite\",false,null]");
            if(retained.write()!=expected)throw std::runtime_error("owned lifetime");
        }
        std::cout<<"MISMATCHES\t"<<mismatches<<"\n";return mismatches?2:0;
    }
    double seconds=argc>3?std::stod(argv[3]):0.5;
    UniValue manifest;if(!manifest.read(Load(dir+"/fixtures.json")))throw std::runtime_error("manifest");
    size_t sink=0;
    std::cout<<"fixture,parser,mode,input_bytes,iterations,seconds,ns_per_iteration,output_bytes,checksum\n";
    for(const auto& item:manifest.getValues()) {
        std::string name=item.get_str(),input=Load(dir+"/"+name+".json");
        auto expected=parsers.Parse(0,input).write();
        for(int p=0;p<3;++p) {
            auto validation=parsers.Parse(p,input).write();if(validation!=expected)throw std::runtime_error("fixture mismatch");
            for(int mode=0;mode<2;++mode) {
                size_t count=0,bytes=0;auto start=std::chrono::steady_clock::now();double elapsed=0;
                do {for(int k=0;k<8;++k){auto owned=parsers.Parse(p,input);if(mode){auto encoded=owned.write();bytes=encoded.size();sink+=bytes;}else sink+=owned.size();++count;}elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();}while(elapsed<seconds);
                std::cout<<name<<','<<p<<','<<(mode?"parse_owned_write":"parse_owned")<<','<<input.size()<<','<<count<<','<<elapsed<<','<<(elapsed*1e9/count)<<','<<bytes<<','<<sink<<'\n';
            }
        }
    }
}
