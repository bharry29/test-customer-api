SELECT 
        H.sopnumbe, 
        L.lnitmseq, 
        H.orignumb,
        CASE 
         WHEN sl.serltnum IS NULL THEN ' ' 
         ELSE sl.serltnum 
       END                       AS SerialNumber, 
        H.CSTPONBR                  AS CustPO,
       l.itemnmbr              AS PartNumber,
       l.quantity              AS Qty, 
        ' '                     AS PartialFilled, 
       H.docdate               AS ShipDate, 
       R.rg_deliverydate       AS DeliveryDate, 
       H.shipmthd              AS ShipMethod, 
        R.rg_Carrier                AS Carrier,
       U.usrdef04                  AS CustShipAcct,
       U.usrdef05              AS TrackingNum,  
        CMT.comment_1               AS Comment,
     H.CUSTNMBR              AS CustomerNum, 
     H.CUSTNAME              AS Custname  
--This is not on the Excel file - but you will need these fields to be able to link back to the Packing Slip
FROM   sop30200 H 
       INNER JOIN sop30300 L 
               ON H.soptype = L.soptype 
                  AND H.sopnumbe = L.sopnumbe 
       INNER JOIN rg_ri_sophdr R 
               ON R.soptype = H.soptype 
                  AND R.sopnumbe = H.sopnumbe 
       LEFT OUTER JOIN sop10106 U 
                    ON U.soptype = H.soptype 
                       AND U.sopnumbe = H.sopnumbe 
        LEFT OUTER JOIN sop10202 CMT
                      ON H.soptype = CMT.soptype
                         AND H.sopnumbe = CMT.sopnumbe
                        AND L.LNITMSEQ = CMT.LNITMSEQ
       LEFT OUTER JOIN rg_ri_itemuserdef I                                              
                    ON I.itemnmbr = L.itemnmbr 
       LEFT OUTER JOIN sop10201 SL 
                    ON L.soptype = SL.soptype 
                       AND L.sopnumbe = SL.sopnumbe 
                       AND L.lnitmseq = SL.lnitmseq 
                       AND L.cmpntseq = SL.cmpntseq 
WHERE  H.soptype in (3, 4) --INVOICE and RETURNS 
       AND H.voidstts = 0 --EXCLUDE VOIDS 
       AND ISNULL(R.RG_OmitFromPortal, 0) = 0    --boolean field - false means to include
       AND H.CSTPONBR <> ''
       AND (H.soptype in (4) OR H.SOPNUMBE NOT IN (SELECT linked_invoices.SOPNUMBE FROM pcbSOPCustomLinkedTo linked_invoices))      AND H.custnmbr IN ('SERV-08', 'SERV-10', 'SERV-11', 'SERV-12', 'SERV-13', 'SERV-14', 'SERV-15', 'SERV-17', 'SERV-18')
--  and H.CUSTNMBR = 'CITI-03' or H.CUSTNMBR = 'CITI-04' or H.CUSTNMBR = 'CITI-07'  --REPLACE WITH THE CUSTOMER NUMBER FOR CITI
UNION
SELECT H.sopnumbe, 
        L.lnitmseq,
        H.orignumb, 
        CASE 
         WHEN sl.serltnum IS NULL THEN ' ' 
         ELSE sl.serltnum 
       END                       AS SerialNumber, 
        H.CSTPONBR                  AS CustPO,
       l.itemnmbr              AS PartNumber,
       l.quantity              AS Qty, 
        ' '                     AS PartialFilled, 
       H.docdate               AS ShipDate, 
       R.rg_deliverydate       AS DeliveryDate, 
       H.shipmthd              AS ShipMethod, 
        R.rg_Carrier                AS Carrier,
       U.usrdef04                  AS CustShipAcct,
       U.usrdef05              AS TrackingNum,  
        CMT.comment_1               AS Comment,
     H.CUSTNMBR              AS CustomerNum, 
     H.CUSTNAME              AS Custname  
--This is not on the Excel file - but you will need these fields to be able to link back to the Packing Slip
FROM   sop10100 H 
       INNER JOIN sop10200 L 
               ON H.soptype = L.soptype 
                  AND H.sopnumbe = L.sopnumbe 
       INNER JOIN rg_ri_sophdr R 
               ON R.soptype = H.soptype 
                  AND R.sopnumbe = H.sopnumbe 
       LEFT OUTER JOIN sop10106 U 
                    ON U.soptype = H.soptype 
                       AND U.sopnumbe = H.sopnumbe 
        LEFT OUTER JOIN sop10202 CMT
                      ON H.soptype = CMT.soptype
                         AND H.sopnumbe = CMT.sopnumbe
                        AND L.LNITMSEQ = CMT.LNITMSEQ
       LEFT OUTER JOIN rg_ri_itemuserdef I 
                    ON I.itemnmbr = L.itemnmbr 
       LEFT OUTER JOIN sop10201 SL 
                    ON L.soptype = SL.soptype 
                       AND L.sopnumbe = SL.sopnumbe 
                       AND L.lnitmseq = SL.lnitmseq 
                       AND L.cmpntseq = SL.cmpntseq 
WHERE  H.soptype IN ( 3, 2, 4 )--INVOICE or ORDERS or RETURNS ONLY 
       AND H.voidstts = 0 --EXCLUDE VOIDS 
       AND ISNULL(R.RG_OmitFromPortal, 0) = 0    --boolean field - false means to include
       AND H.CSTPONBR <> ''
       AND (H.soptype in (2, 4) OR H.SOPNUMBE NOT IN (SELECT linked_invoices.SOPNUMBE FROM pcbSOPCustomLinkedTo linked_invoices))
        AND H.custnmbr IN ('SERV-08', 'SERV-10', 'SERV-11', 'SERV-12', 'SERV-13', 'SERV-14', 'SERV-15', 'SERV-17', 'SERV-18')
UNION ALL
SELECT
        custom_hdr.INVCNMBR as sopnumbe,
        custom_hdr.RecordID as lnitmseq,
        ''                      as orignumb,
        CASE
         WHEN custom_serial.SERLNMBR IS NULL THEN ' '
         ELSE custom_serial.SERLNMBR
       END                     AS SerialNumber,
        custom_hdr.CSTPONBR         AS   CustPO,
       custom_line.itemnmbr              AS PartNumber,
       custom_line.quantity              AS Qty,
       ' '                     AS PartialFilled,
       custom_hdr.DOCDATE               AS ShipDate,
       LinkedR.rg_deliverydate       AS DeliveryDate,
       LinkedH.shipmthd              AS ShipMethod,
        LinkedR.rg_Carrier            AS Carrier,
        LinkedU.usrdef04                   AS CustShipAcct,
       LinkedU.usrdef05              AS TrackingNum,
        CMT.comment_1                AS Comment,
     custom_hdr.CUSTNMBR              AS CustomerNum,
     custom_hdr.CUSTNAME                AS Custname
--This is not on the Excel file - but you will need these fields to be able to link back to the Packing Slip
FROM   pcbSOPHdrCustom custom_hdr
  INNER JOIN pcbSOPLineCustom custom_line ON custom_hdr.CUSTNMBR = custom_line.CUSTNMBR AND custom_hdr.RecordID = custom_line.RecordID
  LEFT JOIN SOP30200 LinkedH ON LinkedH.SOPNUMBE = custom_line.SOPNUMBE AND LinkedH.SOPTYPE = 3
  INNER JOIN RG_RI_SOPHDR LinkedR ON LinkedR.SOPTYPE = 3 AND LinkedR.SOPNUMBE = custom_line.SOPNUMBE
  LEFT OUTER JOIN SOP10106 LinkedU ON LinkedU.SOPTYPE = 3 AND LinkedU.SOPNUMBE = custom_line.SOPNUMBE
    LEFT OUTER JOIN sop10202 CMT
                         ON custom_line.sopnumbe = CMT.sopnumbe
                        AND custom_line.RecordID = CMT.LNITMSEQ
  INNER JOIN RG_RI_ItemUserDef LinkedI ON LinkedI.ITEMNMBR = custom_line.ITEMNMBR
  left outer join pcbSOPSerialCustom custom_serial on custom_hdr.CUSTNMBR = custom_serial.CUSTNMBR AND custom_hdr.RecordID = custom_serial.RecordID and custom_serial.LineSeq = custom_line.LineSeq and custom_serial.CMPNTSEQ = custom_line.CMPNTSEQ
WHERE ISNULL(custom_hdr.PortalScenario, 0) = 0
    AND LinkedH.custnmbr IN ('SERV-08', 'SERV-10', 'SERV-11', 'SERV-12', 'SERV-13', 'SERV-14', 'SERV-15', 'SERV-17', 'SERV-18')
--  and H.CUSTNMBR = 'CITI-03'  --REPLACE WITH THE CUSTOMER NUMBER FOR CITI
ORDER BY ShipDate desc
