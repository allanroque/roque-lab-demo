async function loadJSON(url){
    const res = await fetch(url, {cache:"no-store"});
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
  function setText(id, txt){ const el=document.getElementById(id); if(el) el.textContent=(txt ?? "—"); }
  function setPre(id, txt){ const el=document.getElementById(id); if(el) el.textContent=(txt && String(txt).trim().length ? txt : "—"); }
  function addRow(tbodyId, k, v){
    const tb=document.getElementById(tbodyId); if(!tb) return;
    const tr=document.createElement("tr");
    const td1=document.createElement("td"); td1.textContent=k;
    const td2=document.createElement("td"); td2.textContent=(v ?? "—");
    tr.append(td1,td2); tb.appendChild(tr);
  }
  // Extrai campos de psql_basic
  function parseBasicsBlock(text){
    if(!text) return {};
    const lines=String(text).split(/\r?\n/).map(l=>l.trim()).filter(Boolean);
    const out={};
    for(const l of lines){
      if(l.startsWith("PostgreSQL")) out.version=l;
      else if(l==="localhost") out.listen=l;
      else if(/^\d{4,5}$/.test(l)) out.port=l;
      else if(l.includes("postgresql.conf")) out.config_file=l;
      else if(l.includes("pg_hba.conf")) out.hba_file=l;
      else if(/^\d+$/.test(l)) out.connections=l;
    }
    return out;
  }

  (async ()=>{
    try{
      const data = await loadJSON("health.json");

      // Header
      setText("host", data.host);
      setText("collected", data.collected_at);
      setText("collected-hero", data.collected_at);
      const hh=document.getElementById("hero-host"); if(hh) hh.textContent=data.host||"-";

      // CORE
      addRow("os-kv","OS",data.os?.distro);
      addRow("os-kv","Kernel",data.os?.kernel);
      addRow("os-kv","Arch",data.os?.arch);
      addRow("os-kv","Uptime",data.os?.uptime);
      addRow("os-kv","vCPUs",data.os?.cpu_vcpus);
      addRow("os-kv","Memória (MB)",data.os?.mem_mb);
      addRow("os-extra","Mounts",(data.os?.mounts||[]).join(", "));

      // THP em linha única
      addRow("os-extra","THP",(data.os?.thp||"").toString().replace(/\n/g,"  "));

      // sysctl em chave=valor
      const sys = data.os?.sysctl_sample || [];
      sys.forEach((line,i)=>{
        const s=(line||"").toString().trim(); if(!s) return;
        const [k,v]= s.includes("=") ? s.split("=",2) : [`sysctl#${i+1}`, s];
        addRow("os-extra",k,v);
      });
      setPre("dns-info", data.os?.dns);

      // SERVICE
      setPre("svc-status", data.service?.status);
      setPre("svc-bin", data.service?.bin_version);
      setPre("svc-dirs", data.service?.dirs);

      // NETWORK
      setPre("net-info", data.service?.network);

      // AUTH
      setPre("hba-head", data.postgres?.hba_head);

      // DB BASICS & ACTIVITY
      const basics = parseBasicsBlock(data.postgres?.basics);
      addRow("db-basics","Versão", basics.version);
      addRow("db-basics","Listen", basics.listen);
      addRow("db-basics","Porta", basics.port);
      addRow("db-basics","postgresql.conf", basics.config_file);
      addRow("db-basics","pg_hba.conf", basics.hba_file);
      addRow("db-activity","Conexões (psql_basic)", basics.connections);
      setPre("pg-configs", data.postgres?.configs);

      // ACCESS
      setPre("pg-accounts", data.postgres?.accounts);

      // CONNECTIONS
      setPre("pg-conns", data.postgres?.connections);
      setPre("pg-idle", data.postgres?.idle_in_txn);

      // STORAGE / WAL
      setPre("db-sizes", data.postgres?.db_sizes);
      setPre("pg-disk", data.postgres?.disk);
      setPre("pg-wal", data.postgres?.wal);

      // SCHEMAS / EXTENSIONS
      setPre("pg-ext", data.postgres?.extensions_schemas);
      setPre("pg-schema", data.postgres?.schema_details);

      // REPLICATION / HOT TABLES
      setPre("pg-repl", data.postgres?.replication_hot);

      // RAW JSON
      setPre("raw-json", JSON.stringify(data, null, 2));
    }catch(err){
      setPre("raw-json", "Falha ao carregar health.json: "+err.message);
    }
  })();