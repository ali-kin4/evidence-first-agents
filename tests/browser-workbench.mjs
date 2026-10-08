import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const URL = process.env.EFA_URL || "http://127.0.0.1:8766";
const dir = "screenshots";
await mkdir(dir, {recursive:true});
const errors = [];
let browser;
function requireThat(ok, message) {if(!ok)throw new Error(message);}
async function run(){
  browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  const page=await browser.newPage({viewport:{width:1440,height:960},deviceScaleFactor:1,acceptDownloads:true});
  page.on("pageerror",error=>errors.push(error.message));
  page.on("console",message=>{if(message.type()==="error")errors.push("console: "+message.text());});
  await page.goto(URL,{waitUntil:"domcontentloaded"});
  await page.locator(".metric-card").first().waitFor({timeout:20000});
  requireThat(await page.locator(".metric-card").count()===4,"Overview metrics missing");
  requireThat(await page.locator("#decisionText").innerText()==="FAIL","Expected unsafe fixture scan");
  await page.screenshot({path:dir+"/01-authority-overview.png",fullPage:true});
  await page.locator('[data-view="scenarios"]').click();
  await page.locator(".scenario-card").first().waitFor();
  requireThat(await page.locator(".scenario-card").count()===4,"Missing workshop scenarios");
  await page.screenshot({path:dir+"/02-scenario-library.png",fullPage:true});
  await page.locator('[data-case="safe"]').click();
  await page.locator("#decisionText").getByText("READY").waitFor();
  await page.locator('#scenarioSelect').selectOption("unsafe");
  await page.locator("#decisionText").getByText("FAIL").waitFor();
  await page.locator('[data-view="authority"]').click();
  await page.locator(".authority-block.capability").first().waitFor();
  await page.screenshot({path:dir+"/03-authority-map.png",fullPage:true});
  await page.locator('[data-view="findings"]').click();
  await page.locator(".finding-card").first().waitFor();
  requireThat(await page.locator(".finding-card").count()===3,"Expected three unsafe findings");
  await page.screenshot({path:dir+"/04-finding-explorer.png",fullPage:true});
  await page.locator("#findingSearch").fill("approval");
  requireThat(await page.locator(".finding-card").count()===1,"Finding search broken");
  await page.locator('[data-view="lab"]').click();
  requireThat(await page.locator('input[name="controls"]:checked').count()===3,
    "Expected three suggested remediation controls");
  await page.screenshot({path:dir+"/05-remediation-before.png",fullPage:true});
  await page.locator("#simulateButton").click();
  await page.locator(".comparison-state.after h4").getByText("READY").waitFor({timeout:25000});
  requireThat((await page.locator("#labComparison").innerText()).includes("EMBEDDED_SECRET"),
    "Missing real rescan resolution");
  await page.screenshot({path:dir+"/06-remediation-rescan.png",fullPage:true});
  await page.locator('[data-view="training"]').click();
  requireThat(await page.locator(".training-step").count()===5,"Training walkthrough incomplete");
  await page.screenshot({path:dir+"/07-facilitator-workshop.png",fullPage:true});
  const downloadPromise=page.waitForEvent("download");
  await page.locator("#exportReport").click();
  const exported=await downloadPromise;
  requireThat(exported.suggestedFilename().endsWith(".json"),"Evidence export not JSON");
  await page.setViewportSize({width:390,height:844});
  await page.reload({waitUntil:"domcontentloaded"});
  await page.locator(".metric-card").first().waitFor();
  await page.waitForTimeout(360);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
  if(overflow){
    const offenders=await page.evaluate(()=>Array.from(document.querySelectorAll("body *"))
      .filter(el=>el.getBoundingClientRect().right>window.innerWidth+1 && getComputedStyle(el).display!=="none")
      .slice(0,12).map(el=>({tag:el.tagName,id:el.id,
        className:typeof el.className==="string"?el.className:"",
        right:Math.round(el.getBoundingClientRect().right)})));
    throw new Error("Mobile horizontal overflow: "+JSON.stringify(offenders));
  }
  await page.screenshot({path:dir+"/08-mobile-overview.png",fullPage:true});
  await page.locator("#menuButton").click();
  await page.locator("#sidebar.open").waitFor();
  await page.locator('[data-view="findings"]').click();
  await page.locator("#screen-findings.active").waitFor();
  requireThat(await page.locator("#scrim").isHidden(),"Mobile scrim not dismissed");
  await page.screenshot({path:dir+"/09-mobile-findings.png",fullPage:true});
  requireThat(errors.length===0,"Browser errors: "+errors.join("\n"));
  console.log("PASS: real API data, all scenarios, map, findings, remediation, export, trainer guide and mobile");
}
try{await run();}
catch(err){
  console.error("FAIL browser: "+(err.stack||err));
  if(browser){const p=browser.contexts().flatMap(x=>x.pages())[0];
    if(p)await p.screenshot({path:dir+"/failure.png",fullPage:true}).catch(()=>{});}
  process.exitCode=1;
}finally{if(browser)await browser.close();}
