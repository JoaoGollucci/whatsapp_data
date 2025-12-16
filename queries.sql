-- SELECT
--   SAFE.PARSE_JSON(line) AS raw
-- FROM `gauge-prod.projeto_meli.waha_events_raw_str`
-- LIMIT 10;

-- CREATE OR REPLACE TABLE `gauge-prod.projeto_meli.waha_events_raw`
-- AS
-- SELECT
--   SAFE.PARSE_JSON(line) AS raw
-- FROM `gauge-prod.projeto_meli.waha_events_raw_str`;

-- SILVER V1
with dados as (
	select
	JSON_VALUE(raw, '$.event') as type,
	JSON_VALUE(raw, '$.message_id') as id,
	COALESCE(JSON_VALUE(raw, '$.payload._data.Info.SenderAlt'), 'N/A') as sender,
	DATE(DATETIME(TIMESTAMP(JSON_VALUE(raw, '$.payload._data.Info.Timestamp')), "America/Sao_Paulo")) as date,
	TIME(DATETIME(TIMESTAMP(JSON_VALUE(raw, '$.payload._data.Info.Timestamp')), "America/Sao_Paulo")) as time,
	JSON_VALUE(raw, '$.payload._data.Message.imageMessage.caption') as caption,
	JSON_VALUE(raw, '$.payload.body') as body,
	raw.payload as payload,
	from `gauge-prod.projeto_meli.waha_events_raw`
)
select id,
date,
time,
SUBSTRING(split(sender, '@')[0], 0, 2) as contry_code,
SUBSTRING(split(sender, '@')[0], 3, 2) as state_code,
SUBSTRING(split(sender, '@')[0], 5, (length(split(split(sender, '@')[0],':')[0]))-4) as tel_number,
COALESCE(caption, 'N/A') as caption,
COALESCE(body, 'N/A') as body,
from dados
where date >= '2025-11-14'
AND time >= '11:30:00'
AND length(sender)>2

-- GOLD V1
CREATE OR REPLACE TABLE `gauge-prod.projeto_meli.gold_messages`
AS
with base as (
	select distinct
	id,
	date,
	time,
	contry_code as country_code,
	state_code,
	tel_number,
	case
		-- ECOMMERCE
	when lower(body) like '%mercadolivre%' or lower(caption) like '%mercadolivre%' then 'MERCADO LIVRE'
	when lower(body) like '%magalu%' or lower(caption) like '%magalu%' then 'MAGAZINE LUIZA'
	when lower(body) like '%magazinevoce%' or lower(caption) like '%magazinevoce%' then 'MAGAZINE LUIZA'
	when lower(body) like '%magazineluiza.onelink%' or lower(caption) like '%magazineluiza.onelink%' then 'MAGAZINE LUIZA'
	when lower(body) like '%magazineluiza.com%' or lower(caption) like '%magazineluiza.com%' then 'MAGAZINE LUIZA'
	when lower(body) like '%shopee%' or lower(caption) like '%shopee%' then 'SHOPEE'
	when lower(body) like '%br.shp.ee%' or lower(caption) like '%br.shp.ee%' then 'SHOPEE'
	when lower(body) like '%amzn%' or lower(caption) like '%amzn%' then 'AMAZON'
	when lower(body) like '%amzlink%' or lower(caption) like '%amzlink%' then 'AMAZON'
	when lower(body) like '%amazon%' or lower(caption) like '%amazon%' then 'AMAZON'
	when lower(body) like '%shein%' or lower(caption) like '%shein%' then 'SHEIN'
	when lower(body) like '%natura.com%' or lower(caption) like '%natura.com%' then 'NATURA'
	when lower(body) like '%natura.divulgador%' or lower(caption) like '%natura.divulgador%' then 'NATURA'
	when lower(body) like '%s.click.aliexpress.com%' or lower(caption) like '%s.click.aliexpress.com%' then 'ALIEXPRESS'
	when lower(body) like '%pt.aliexpress.com%' or lower(caption) like '%pt.aliexpress.com%' then 'ALIEXPRESS'
	when lower(body) like '%a.aliexpress.com%' or lower(caption) like '%a.aliexpress.com%' then 'ALIEXPRESS'
	when lower(body) like '%ofertou.ai%aliexpress%' or lower(caption) like '%ofertou.ai%aliexpress%' then 'ALIEXPRESS'
	when lower(body) like '%epocacosmeticos%' or lower(caption) like '%epocacosmeticos%' then 'EPOCA COSMETICOS'
	when lower(body) like '%sephora.com%' or lower(caption) like '%sephora.com%' then 'SEPHORA'
	when lower(body) like '%lancome.com%' or lower(caption) like '%lancome.com%' then 'LANCOME'
	when lower(body) like '%terabyteshop%' or lower(caption) like '%terabyteshop%' then 'TERABYTE'
	when lower(body) like '%ofertou.ai%terabyte%' or lower(caption) like '%ofertou.ai%terabyte%' then 'TERABYTE'
	when lower(body) like '%minhacea%' or lower(caption) like '%minhacea%' then 'C&A'
	when lower(body) like '%.cea.com%' or lower(caption) like '%.cea.com%' then 'C&A'
	when lower(body) like '%muranojoias.com%' or lower(caption) like '%muranojoias.com%' then 'MURANO JOIAS'
	when lower(body) like '%boticario.com%' or lower(caption) like '%boticario.com%' then 'BOTICÁRIO'
	when lower(body) like '%quemdisseberenice.com%' or lower(caption) like '%quemdisseberenice.com%' then 'QUEM DISSE BERENICE'
	when lower(body) like '%farmrio.com%' or lower(caption) like '%farmrio.com%' then 'FARM RIO'
	when lower(body) like '%zzmall.com%' or lower(caption) like '%zzmall.com%' then 'ZZ MALL'
	when lower(body) like '%.paguemenos.com%' or lower(caption) like '%.paguemenos.com%' then 'FARMÁCIA PAGUE MENOS'
	when lower(body) like '%click.nike.com%' or lower(caption) like '%click.nike.com%' then 'NIKE'
	when lower(body) like '%ybera.com%' or lower(caption) like '%ybera.com%' then 'YBERA'
	when lower(body) like '%.amobeleza.com%' or lower(caption) like '%.amobeleza.com%' then 'AMO BELEZA'
	when lower(body) like '%netshoes.com%' or lower(caption) like '%netshoes.com%' then 'NETSHOES'
	when lower(body) like '%store.epicgames.com%' or lower(caption) like '%store.epicgames.com%' then 'EPIC GAMES'
	when lower(body) like '%.tim.com%' or lower(caption) like '%.tim.com%' then 'TIM'
	when lower(body) like '%.olx.com%' or lower(caption) like '%.olx.com%' then 'OLX'
	when lower(body) like '%.creamy.com%' or lower(caption) like '%.creamy.com%' then 'CREAMY'
	when lower(body) like '%.skyn.com%' or lower(caption) like '%.skyn.com%' then 'SKYN'
	when lower(body) like '%click.centauro.com%' or lower(caption) like '%click.centauro.com%' then 'CENTAURO'
	when lower(body) like '%gsuplementos.com%' or lower(caption) like '%gsuplementos.com%' then 'GROWTH'
	when lower(body) like '%.brae.com%' or lower(caption) like '%.brae.com%' then 'BRAE'
	when lower(body) like '%/elausa.com%' or lower(caption) like '%/elausa.com%' then 'ELA USA'
	when lower(body) like '%/queridocuidado.com%' or lower(caption) like '%/queridocuidado.com%' then 'QUERIDO CUIDADO'
	when lower(body) like '%ifood.com%' or lower(caption) like '%ifood.com%' then 'IFOOD'
	when lower(body) like '%99app.com%' or lower(caption) like '%99app.com%' then '99'
	when lower(body) like '%.riachuelo.com%' or lower(caption) like '%.riachuelo.com%' then 'RIACHUELO'
	when lower(body) like '%powerupinfo.com%' or lower(caption) like '%powerupinfo.com%' then 'POWER UP INFO'
	when lower(body) like '%granado.com%' or lower(caption) like '%granado.com%' then 'GRANADO'
	when lower(body) like '%havaianas.com%' or lower(caption) like '%havaianas.com%' then 'HAVAIANAS'
	when lower(body) like '%lojasrenner.com%' or lower(caption) like '%lojasrenner.com%' then 'RENNER'
	when lower(body) like '%dafiti.com%' or lower(caption) like '%dafiti.com%' then 'DAFITI'
	when lower(body) like '%airbnb.com%' or lower(caption) like '%airbnb.com%' then 'AIRBNB'
	when lower(body) like '%nacasachinatem.com%' or lower(caption) like '%nacasachinatem.com%' then 'CASA CHINA'
	when lower(body) like '%skelt.com%' or lower(caption) like '%skelt.com%' then 'SKELT'
	when lower(body) like '%belezabrasileira.com%' or lower(caption) like '%belezabrasileira.com%' then 'BELEZA BRASILEIRA'
	when lower(body) like '%eudora.com%' or lower(caption) like '%eudora.com%' then 'EUDORA'
	when lower(body) like '%polishop.com%' or lower(caption) like '%polishop.com%' then 'POLISHOP'
	when lower(body) like '%vivara.com%' or lower(caption) like '%vivara.com%' then 'VIVARA'
	when lower(body) like '%steampowered.com%' or lower(caption) like '%steampowered.com%' then 'STEAM'
	when lower(body) like '%pichau.com%' or lower(caption) like '%pichau.com%' then 'PICHAU'
	when lower(body) like '%centauro.com%' or lower(caption) like '%centauro.com%' then 'CENTAURO'
	when lower(body) like '%.semparar.com%' or lower(caption) like '%.semparar.com%' then 'SEM PARAR'
	when lower(body) like '%.thejoylab.com%' or lower(caption) like '%.thejoylab.com%' then 'JOY LAB'
	when lower(body) like '%.rohtobrasil.com%' or lower(caption) like '%.rohtobrasil.com%' then 'ROHTO'
	when lower(body) like '%.oceane.com%' or lower(caption) like '%.oceane.com%' then 'OCEANE'
		-- AGREGADORES
	when lower(body) like '%achadosprincipais%' or lower(caption) like '%achadosprincipais%' then 'AGREGADOR'
	when lower(body) like '%promorelampago%' or lower(caption) like '%promorelampago%' then 'AGREGADOR'
	when lower(body) like '%minhaloja.%' or lower(caption) like '%minhaloja.%' then 'AGREGADOR'
	when lower(body) like '%https://achad%.com%' or lower(caption) like '%https://achad%.com%' then 'AGREGADOR'
	when lower(body) like '%https://%promo%.com%' or lower(caption) like '%https://%promo%.com%' then 'AGREGADOR'
	when lower(body) like '%https://%promo%/%' or lower(caption) like '%https://%promo%/%' then 'AGREGADOR'
	when lower(body) like '%homedeamiga%' or lower(caption) like '%homedeamiga%' then 'AGREGADOR'
	when lower(body) like '%belezanaweb%' or lower(caption) like '%belezanaweb%' then 'AGREGADOR'
	when lower(body) like '%pincei.co%' or lower(caption) like '%pincei.co%' then 'AGREGADOR'
	when lower(body) like '%ofertasdahoradoalmoco.com%' or lower(caption) like '%ofertasdahoradoalmoco.com%' then 'AGREGADOR'
	when lower(body) like '%temdetudotchelo.com%' or lower(caption) like '%temdetudotchelo.com%' then 'AGREGADOR'
	when lower(body) like '%compre.link%' or lower(caption) like '%compre.link%' then 'AGREGADOR'
	when lower(body) like '%helainevieira.com%' or lower(caption) like '%helainevieira.com%' then 'AGREGADOR'
	when lower(body) like '%topdescontos.com%' or lower(caption) like '%topdescontos.com%' then 'AGREGADOR'
	when lower(body) like '%adivulgadora.com%' or lower(caption) like '%adivulgadora.com%' then 'AGREGADOR'
	when lower(body) like '%oferta.jersuindica.com%' or lower(caption) like '%oferta.jersuindica.com%' then 'AGREGADOR'
	when lower(body) like '%ratadosachados.com%' or lower(caption) like '%ratadosachados.com%' then 'AGREGADOR'
	when lower(body) like '%seguidoradeoportunidade.com%' or lower(caption) like '%seguidoradeoportunidade.com%' then 'AGREGADOR'
	when lower(body) like '%baratinhosimperdiveis.com%' or lower(caption) like '%baratinhosimperdiveis.com%' then 'AGREGADOR'
	when lower(body) like '%clube.baby%' or lower(caption) like '%clube.baby%' then 'AGREGADOR'
	when lower(body) like '%dicasdalima.com%' or lower(caption) like '%dicasdalima.com%' then 'AGREGADOR'
	when lower(body) like '%ofertasmaiscupons.com%' or lower(caption) like '%ofertasmaiscupons.com%' then 'AGREGADOR'
	when lower(body) like '%descontolegal.com%' or lower(caption) like '%descontolegal.com%' then 'AGREGADOR'
	when lower(body) like '%anabeltrandicas.com%' or lower(caption) like '%anabeltrandicas.com%' then 'AGREGADOR'
	when lower(body) like '%guiadecomprasnaweb.com%' or lower(caption) like '%guiadecomprasnaweb.com%' then 'AGREGADOR'
	when lower(body) like '%railaneramos.com%' or lower(caption) like '%railaneramos.com%' then 'AGREGADOR'
	when lower(body) like '%dicasdeachados.com%' or lower(caption) like '%dicasdeachados.com%' then 'AGREGADOR'
	when lower(body) like '%modacasakids.com%' or lower(caption) like '%modacasakids.com%' then 'AGREGADOR'
	when lower(body) like '%mipires.com%' or lower(caption) like '%mipires.com%' then 'AGREGADOR'
	when lower(body) like '%railaneramos.com%' or lower(caption) like '%railaneramos.com%' then 'AGREGADOR'
	when lower(body) like '%byachadosdamari.com%' or lower(caption) like '%byachadosdamari.com%' then 'AGREGADOR'
	when lower(body) like '%ofertas.meuape26b.com%' or lower(caption) like '%ofertas.meuape26b.com%' then 'AGREGADOR'
	when lower(body) like '%ofertou.ai%' or lower(caption) like '%ofertou.ai%' then 'AGREGADOR'
	when lower(body) like '%focanacompra.com%' or lower(caption) like '%focanacompra.com%' then 'AGREGADOR'
	when lower(body) like '%barbieconsumista.com%' or lower(caption) like '%barbieconsumista.com%' then 'AGREGADOR'
	when lower(body) like '%o.tabugado.com%' or lower(caption) like '%o.tabugado.com%' then 'AGREGADOR'
	when lower(body) like '%divulgadorinteligente.com%' or lower(caption) like '%divulgadorinteligente.com%' then 'AGREGADOR'
	when lower(body) like '%quenotebookcomprar.com%' or lower(caption) like '%quenotebookcomprar.com%' then 'AGREGADOR'
	when lower(body) like '%paraisodosachadinhos.com%' or lower(caption) like '%paraisodosachadinhos.com%' then 'AGREGADOR'
	when lower(body) like '%preguicaofertas.com%' or lower(caption) like '%preguicaofertas.com%' then 'AGREGADOR'
	when lower(body) like '%.achamospravc.com%' or lower(caption) like '%.achamospravc.com%' then 'AGREGADOR'
	when lower(body) like '%achadinhosdasprimas.com%' or lower(caption) like '%achadinhosdasprimas.com%' then 'AGREGADOR'
	when lower(body) like '%/pobres.com%' or lower(caption) like '%/pobres.com%' then 'AGREGADOR'
		-- BETS
	when lower(body) like '%aa7.%' or lower(caption) like '%aa7.%' then 'BETS'
	when lower(body) like '%bmw7.%' or lower(caption) like '%bmw7.%' then 'BETS'
		--ENCURTADOR
	when lower(body) like '%tinyurl%' or lower(caption) like '%tinyurl%' then 'ENCURTADOR'
	when lower(body) like '%blz.to%' or lower(caption) like '%blz.to%' then 'ENCURTADOR'
	when lower(body) like '%desc.vc%' or lower(caption) like '%desc.vc%' then 'ENCURTADOR'
	when lower(body) like '%tidd.ly%' or lower(caption) like '%tidd.ly%' then 'ENCURTADOR'
	when lower(body) like '%busqy.me%' or lower(caption) like '%busqy.me%' then 'ENCURTADOR'
	when lower(body) like '%is.gd%' or lower(caption) like '%is.gd%' then 'ENCURTADOR'
	when lower(body) like '%cutt.ly%' or lower(caption) like '%cutt.ly%' then 'ENCURTADOR'
	when lower(body) like '%lnk.do%' or lower(caption) like '%lnk.do%' then 'ENCURTADOR'
	when lower(body) like '%rstyle.me%' or lower(caption) like '%rstyle.me%' then 'ENCURTADOR'
	when lower(body) like '%reduz.me%' or lower(caption) like '%reduz.me%' then 'ENCURTADOR'
	when lower(body) like '%t.co/%' or lower(caption) like '%t.co/%' then 'ENCURTADOR'
	when lower(body) like '%bit.ly%' or lower(caption) like '%bit.ly%' then 'ENCURTADOR'
	when lower(body) like '%tabara.to%' or lower(caption) like '%tabara.to%' then 'ENCURTADOR'
	when lower(body) like '%mais.app%' or lower(caption) like '%mais.app%' then 'ENCURTADOR'
	when lower(body) like '%shorty.ninja%' or lower(caption) like '%shorty.ninja%' then 'ENCURTADOR'
	when lower(body) like '%shre.ink%' or lower(caption) like '%shre.ink%' then 'ENCURTADOR'
	when lower(body) like '%wa.me%' or lower(caption) like '%wa.me%' then 'ENCURTADOR'
	when lower(body) like '%tiddly.xyz%' or lower(caption) like '%tiddly.xyz%' then 'ENCURTADOR'
	when lower(body) like '%tr.ee%' or lower(caption) like '%tr.ee%' then 'ENCURTADOR'
	when lower(body) like '%/a.co%' or lower(caption) like '%/a.co%' then 'ENCURTADOR'
	when lower(body) like '%abrir.link%' or lower(caption) like '%abrir.link%' then 'ENCURTADOR'
	when lower(body) like '%lmdee.link%' or lower(caption) like '%lmdee.link%' then 'ENCURTADOR'
		--OUTROS
	when lower(body) like '%instagram.com%' or lower(caption) like '%instagram.com%' then 'INSTAGRAM'
	when lower(body) like '%https://x.com%' or lower(caption) like '%https://x.com%' then 'TWITTER'
	else 'OUTROS' end as origin,
		case
		when lower(body) like '%cupom%' or lower(caption) like '%cupom%' then True
		else False end as coupon,
			-- body,
-- caption
from `gauge-prod.projeto_meli.silver_messages`
)
select base.*,
grupos.aff_id as aff_id,
grupos.class_atual as class,
grupos.grupo as group_name,
'to_process' as category
from base as base
left join `gauge-prod.projeto_meli.base_grupos` as grupos
ON split(base.id, '_')[1] = grupos.id_api
-- where origin = 'OUTROS'
where origin <> 'OUTROS'

-- INSERT DO BATCH
insert into `projeto_meli.silver_messages`
with batch_fill as (
	SELECT DISTINCT
	id,
	DATE(DATETIME(TIMESTAMP_SECONDS(timestamp), "America/Sao_Paulo")) AS date,
	TIME(DATETIME(TIMESTAMP_SECONDS(timestamp), "America/Sao_Paulo")) AS time,
	SUBSTRING(split(_data.Info.SenderAlt, '@')[0], 0, 2) as contry_code,
	SUBSTRING(split(_data.Info.SenderAlt, '@')[0], 3, 2) as state_code,
	SUBSTRING(split(_data.Info.SenderAlt, '@')[0], 5, (length(split(split(_data.Info.SenderAlt, '@')[0],':')[0]))-4) as tel_number,
	COALESCE(body, 'N/A') as body,
	COALESCE(_data.Message.imageMessage.caption, 'N/A') as caption
	FROM `gauge-prod.projeto_meli.raw_batch`
	WHERE id not in (select distinct id from `projeto_meli.silver_messages` where date = current_date()-1)
	AND length(_data.Info.SenderAlt)>2
)
select * from batch_fill
where (body != 'N/A' or caption != 'N/A') 
AND date = current_date()-1
