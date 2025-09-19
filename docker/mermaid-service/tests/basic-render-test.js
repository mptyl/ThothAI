import { MermaidRenderer, closeBrowser } from '../src/renderer.js';
import { DEFAULT_MERMAID_CONFIG } from '../src/config.js';

const SAMPLE_ERD = `erDiagram
    book ||--|| product : "id = id"
    cdrom ||--|| product : "id = id"
    classif2classif }o--|| classification : "rightclassif_id = id"
    classif2classif }o--|| classificationtype : "classiftype_id = code"
    classif2classif }o--|| classification : "leftclassif_id = id"
    classification }o--|| classification : "parent_id = id"
    classification }o--|| classificationtype : "classiftype_id = code"
    classificationtext }o--|| classification : "classification_id = id"
    clastype2clastype }o--|| classificationtype : "tclasstype = code"
    clastype2clastype }o--|| classificationtype : "pclasstype = code"
    component }o--|| product : "product_id = id"
    course ||--|| product : "id = id"
    credit }o--|| creditsupplier : "creditsupplier_id = id"
    credit }o--|| productitem : "productitem_id = id"
    pricegroup }o--|| pricegroup : "unipricegroupcode = code"
    prj2extreference }o--|| externalreference : "extreference_id = id"
    prj2extreference }o--|| project : "project_id = id"
    prj2prj }o--|| project : "leftproject_id = id"
    prj2prj }o--|| project : "rightproject_id = id"
    prj2prj }o--|| relationshiptype : "reltype_code = code"
    process }o--|| stage : "currstage_id = id"
    process }o--|| project : "project_id = id"
    process }o--|| processtype : "processtype_id = id"
    process }o--|| productitem : "productitem_id = id"
    prod2prod }o--|| product : "rightproduct_id = id"
    prod2prod }o--|| relationshiptype : "reltype_code = code"
    prod2prod }o--|| product : "leftproduct_id = id"
    proditem2component }o--|| component : "component_id = id"
    proditem2component }o--|| productitem : "proditem_id = id"
    product }o--|| prodsubtype : "subtype_id = code"
    product2classification }o--|| classificationtype : "classiftype_id = code"
    product2classification }o--|| classification : "classification_id = id"
    product2classification }o--|| product : "product_id = id"
    productitem }o--|| product : "product_id = id"
    productitem2teacher }o--|| teacher : "teacher_id = id"
    productitem2teacher }o--|| productitem : "productitem_id = id"
    project }o--|| standard : "standard_id = id"
    project2tb }o--|| project : "project_id = id"
    project2tb }o--|| relationshiptype : "reltype_code = code"
    project2tb }o--|| tb : "tb_id = id"
    property }o--|| propertyhelp : "helpname = name"
    property }o--|| stage : "stage_id = id"
    property }o--|| process : "process_id = id"
    stage }o--|| stagetype : "stagetype_id = id"
    stage }o--|| process : "process_id = id"
    stagetype }o--|| macrostage : "macrostage_id = id"
    standard ||--|| product : "id = id"
    standard }o--|| pricegroup : "pricegroup_code = code"
    standard }o--|| stdstatus : "status_code = code"
    stddocument ||--|| component : "id = id"
    stddocument }o--|| phasetype : "phase = code"
    stddocument }o--|| phasetype : "sourcesystem = sourcesystem"
    stdtitle }o--|| product : "product_id = id"
    subscription ||--|| product : "id = id"
    tb2tb }o--|| relationshiptype : "reltype_code = code"
    tb2tb }o--|| tb : "lefttb_id = id"
    tb2tb }o--|| tb : "righttb_id = id"
    teacher2classification }o--|| classification : "classification_id = id"
    teacher2classification }o--|| classificationtype : "classiftype_id = code"
    teacher2classification }o--|| teacher : "teacher_id = id"
    teachertext }o--|| teacher : "teacher_id = id"
    user2role }o--|| role : "role_id = role"
    user2role }o--|| user : "user_id = username"
    user2tb }o--|| relationshiptype : "reltype_code = code"
    user2tb }o--|| tb : "tb_id = id"
    user2wfgroup }o--|| user : "user_id = username"
    user2wfgroup }o--|| wfgroup : "group_id = id"`;

const renderer = new MermaidRenderer(DEFAULT_MERMAID_CONFIG);

const run = async () => {
  console.log('Running Mermaid renderer smoke tests...');

  const svgResult = await renderer.render(SAMPLE_ERD, { format: 'svg' });
  if (!svgResult?.svg || !svgResult.svg.includes('<svg')) {
    throw new Error('SVG output did not contain expected <svg> tag');
  }
  console.log(`✓ SVG generated (${svgResult.svg.length} chars)`);

  const pngResult = await renderer.render(SAMPLE_ERD, { format: 'png', scale: 1 });
  if (!pngResult?.png || !(pngResult.png instanceof Uint8Array) || pngResult.png.length === 0) {
    throw new Error('PNG output is empty');
  }
  console.log(`✓ PNG generated (${pngResult.png.length} bytes)`);

  console.log('All Mermaid renderer checks passed.');
};

run().catch((error) => {
  console.error('Mermaid renderer test failed:', error);
  process.exitCode = 1;
}).finally(async () => {
  await closeBrowser();
});
