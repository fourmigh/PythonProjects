@file:Suppress("PropertyName")

package com.tristarinc.library.mxd.file.client

import com.tristarinc.library.currency.CurrencyInfo
import com.tristarinc.library.mxd.bean.DataType
import com.tristarinc.library.mxd.bean.Element
import com.tristarinc.library.mxd.bean.FileType
import com.tristarinc.library.mxd.file.FileMxdUtils
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.bean.Entry
import com.tristarinc.library.mxd.file.enums.*
import java.io.File

class SIN(origin: String, machineUniqueID: Long) : MXD() {

    init {
        create(FileType.SIN, origin, machineUniqueID)
    }

    companion object {

        private const val Default_RejFile = "--------.REJ"
        private const val Default_Validator = "------/---"

        open class Item

        class NameLocation : Item() {
            var Name = ""
            var Location = ""
            var LocationId = ""
            var SerialNoStr = ""
            var UniqueIdentity = 0L
        }

        class PciVersion : Item() {
            var SysVer = "INVALID"
            var SsVer = ArrayList<Int>()
            var SsCRC = ArrayList<Long>()
        }

        class MxdFile : Item() {
            val File = Entry()
        }

        class Boot : Item() {
            var Version = ""
        }

        class Locale : Item() {
            var No = 11
            var Id = ""
            var User = false
            var Maint = false
        }

        class Currency : Item() {
            var No = 0
            var Iso4217Code = CurrencyIso4217Enum.XXX
            var ExchangeRate = 1000
        }

        class Printer : Item() {
            var Type = PrinterTypeEnum.UNKNOWN
            var FwVersion = 0//255
            var FwVersionStr = ""
        }

        class CPLD : Item() {
            var DesignRef = ""
            var Version = ""
        }

        class UpperLock : Item() {
            var UpperLockType = LMCUlockTypeEnum.UNKNOWN
            var UpperLockFwVersion = 0
        }

        class VaultLock : Item() {
            var VaultType = LMCVaultTypeEnum.UNKNOWN
            var VaultFwVersion = 0//255
        }

        class PSU : Item() {
            var ReportWhenMainsOff = false
            var ReportWhenSolarOff = false
            var FwVersion = 0//255
            var BoardIssue = 0//255
        }

        open class SysinfoCash : Item() {
//            var Type = CSMCashSystemTypeEnum.NOT_FITTED
            var Type = CurrencyInfo.NotFound
            var FwVersion = ""
            var RejFile = Default_RejFile
            var Validator = Default_Validator
        }
        class Coin : SysinfoCash()
        class Note : SysinfoCash()

        class Modem : Item() {
            var Name = ""
            var Class = ModemClassEnum.GSM
            var Voice = false
            var No = 0//255
            var ATI2Resp = ""
            var ATCGMMResp = ""
            var ATCGMIResp = ""
            var ATCGMRResp = ""
            var ATCGSNResp = ""
            var ATiRP0Resp = ""
            var ATiRP5Resp = ""
            var ATiRP1Resp = ""
            var ATiMACAResp = ""
            var WizVersion = ""
            var WizMacAddr = ""
            var WizType = ""
            //新西兰新增需求：增加字段
            var UseDhcp                   = 1
            var ATICCIDResp               = ""
            var SignalCSQ                 = 0
            var SignaldBm                 = 0
            var Signalpct                 = 0
            var NetReg                    = ""
            var NwCarrier                 = ""
            var NwTechnology              = ""
        }

        class Cadix : Item() {
            var FwId = ""
            var FwVersion = ""
        }

        class Csc : Item() {
            var SerialNo = 0L//9223372036854775807
            var Release = ""
            var Ux300SerialNumber = ""
            var Ux300SoftwareVersion = ""
            var Ux100SerialNumber = ""
            var Ux100SoftwareVersion = ""
        }

        class Atos : Item() {
            var SoftwareVersion = ""
            var SoftwarePackage = ""
            var SixTerminalId = ""
            var MACAddress = ""
        }

        class CardEase : Item() {
            var OEMId = 9997
            var TerminalId = 0
        }

        class FrontPanel : Item() {
            var FirmwareVersion = 0
            var KeyPadName = ""
        }

        class ChipnPin : Item() {
            var ManufacturerCode = ""
            var SerialNumber = ""
            var ModelNumber = ""
            var SoftwareVersion = 0//65535
        }

        class SwissCash : Item() {
            var TermId = 0L//4294967295
            var FirmwareVersion = ""
            var Enabled276 = false
            var EnabledCash = false
        }

        class Display : Item() {
            var VersionMajor = 0//255
            var VersionMinor = 0//255
            var IMXVersionMajor = 0//255
            var IMXVersionMinor = 0//255
        }

        class Lul : Item() {
            var ListVersion = ""
            var FolderNumber = 0//65535
        }

        class ContactCard : Item() {
            var FwId = ""
            var FwVersion = ""
        }

        class GLOBALCOM_CONFIG_SERIAL_NUMBER {
            var SerialNumber = "xxxxxxxxxxxxx"
        }

        class GLOBALCOM_CONFIG_FIRMWARE_VERSION {
            var FirmwareVersion = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }

        class GlobalCom : Item() {
            val SerialNumber = ArrayList<GLOBALCOM_CONFIG_SERIAL_NUMBER>()
            val FirmwareVersion = ArrayList<GLOBALCOM_CONFIG_FIRMWARE_VERSION>()
            var TerminalId = ""
        }

        class Ingenico : Item() {
            var TerminalId = ""
            var TrmSwVersion = ""
            var VcsSwVersion = ""
            var TerminalSn = ""
            var ContactReaderSn = ""
            var ClessReaderSn = ""
        }

        class Gecr : Item() {
            var SoftwareVersion = ""
        }

        class Voucher : Item() {
            var Enabled = false
            var Present = false
            //-32768~32767
            var NumScans = 0//32767
            var LastScanResult = ""
        }

        class CardReader : Item() {
            var Type = ""
            var SerialNumber1 = ""
            var SerialNumber2 = ""
            var SerialNumber3 = ""
            var ModelNumber = ""
            var SoftwareVersion1 = ""
            var SoftwareVersion2 = ""
            var SoftwareVersion3 = ""
            var SoftwareVersion4 = ""
            var SoftwareVersion5 = ""
            var TID = ""
            var MID = ""
            var OEMID = ""
            var StationID = ""
            var PA_DSS_Version = ""
            var MACAddress = ""
        }

        @Suppress("unused")
        enum class GenCardReaderTypeEnum(val description: String) {
            NONE("Unknown"),
            ATOS("Atos"),
            CADIX("Cadix"),
            CONTACTCARD("ContactCard"),
            CSC("CSC"),
            ING("Ingenico non-CVM"),
            ING_CHIPNPIN("Ingenico ChipnPin"),
            THL_CHIPNPIN("Thales ChipnPin"),
            OTI("OTI London"),
            VERIFONE_VIPA6("Verfone VIPA6"),
            VERIFONE("Verifone"),
            VIVOTECH("VIVO Contactless"),
            WINDCAVE("WindCave"),
            PAX("PAX");
            companion object{
                fun from(description: String): GenCardReaderTypeEnum {
                    return entries.firstOrNull { it.description.uppercase() == description.uppercase() } ?: NONE
                }
            }
        }

        @Suppress("unused")
        class GenCardReaderSwElement {
            var Used = false
            var Desc = ""
            var Version = ""
        }

        @Suppress("unused")
        class GenCardReaderComponent {
            var Used = false
            var Desc = ""
            var SerialNumber = ""
            var SwElement = ArrayList<GenCardReaderSwElement>()
        }

        @Suppress("unused")
        class GenCardReader {
            var Type = GenCardReaderTypeEnum.NONE
            var ModelNumber = ""
            var TID = ""
            var MID = ""
            var OEMID = ""
            var StationID = ""
            var PAA_DSS_Ver = ""
            var Version = ""
            var MACAddr = ""
            var Component = ArrayList<GenCardReaderComponent>()
        }

        @Suppress("unused")
        class GenericCardReader : Item() {
            var CardReader = GenCardReader()
        }

        @Suppress("unused")
        class Processor : Item() {
            var DeviceRevision = 5
            var DeviceFamily  = "4 (K60)"
            var ProgramFlash = "11 (512 KB)"
            var FlexNVM = "11 (512 KB)"
        }

        class CPUBoard : Item() {
            var Revision = "E"
            var Processor = Processor()
        }

        @Suppress("unused")
        class SYSINFO {
            val NameLocation = NameLocation()
            val PciVersion = PciVersion()
            val MxdFile = MxdFile()
            val Boot = Boot()
            val Locale = Locale()
            val Currency = Currency()
            val Printer = Printer()
            val CPLD = CPLD()
            val UpperLock = UpperLock()
            val VaultLock = VaultLock()
            val PSU = PSU()
            val Coin = Coin()
            val Note = Note()
            val Modem = Modem()
            val Cadix = Cadix()
            val Csc = Csc()
            val Atos = Atos()
            val CardEase = CardEase()
            val FrontPanel = FrontPanel()
            val ChipnPin = ChipnPin()
            val SwissCash = SwissCash()
            val Display = Display()
            val Lul = Lul()
            val ContactCard = ContactCard()
            val GlobalCom = GlobalCom()
            val Ingenico = Ingenico()
            val Gecr = Gecr()
            val Voucher = Voucher()
            val CardReader = CardReader()
            val CPUBoard = CPUBoard()
            val GenericCardReader = GenericCardReader()
        }
    }

    private val items = ArrayList<Item>()

    fun addItem(item: Item) {
        items.add(item)

        buildSchema()
    }

    private fun buildSchema() {
        if (items.isEmpty() || schema.isNotEmpty()) {
            return
        }

        //Rec 0:NameLocation
        var record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Name"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Location"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "LocationId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SerialNoStr"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "UniqueIdentity"))
        schema.add(record)

        //Rec 1:PciVersion
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SysVer"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SsVer", true))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SsCRC", true))
        schema.add(record)

        //Rec 2:Entry
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FileSize"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FileCrc"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FileName"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Customer"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CreationTime"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "ContentType"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Version"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EncryptionType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "ValidFromTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CompatibilityLevel"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "CreationTz"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "ValidFromTz"))
        schema.add(record)

        //Rec 3:MxdFile
        record = Element()
        record.elements.add(Element(2, "File"))
        schema.add(record)

        //Rec 4:Boot
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Version"))
        schema.add(record)

        //Rec 5:Locale
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "No"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Id"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "User"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Maint"))
        schema.add(record)

        //Rec 6:Currency
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "No"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Iso4217Code"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "ExchangeRate"))
        schema.add(record)

        //Rec 7:Printer
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "Type"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FwVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FwVersionStr"))
        schema.add(record)

        //Rec 8:CPLD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "DesignRef"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Version"))
        schema.add(record)

        //Rec 9:UpperLock
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "UpperLockType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "UpperLockFwVersion"))
        schema.add(record)

        //Rec 10:VaultLock
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "VaultType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "VaultFwVersion"))
        schema.add(record)

        //Rec 11:PSU
        record = Element()
        record.elements.add(Element(DataType.MXDDT_BOOL, "ReportWhenMainsOff"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "ReportWhenSolarOff"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FwVersion"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "BoardIssue"))
        schema.add(record)

        //Rec 12:SYSINFO_CASH,Coin,Note
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "Type"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FwVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "RejFile"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Validator"))
        schema.add(record)

        //Rec 13:Modem
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Name"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Class"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Voice"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "No"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATI2Resp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATCGMMResp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATCGMIResp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATCGMRResp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATCGSNResp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATiRP0Resp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATiRP5Resp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATiRP1Resp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATiMACAResp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "WizVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "WizMacAddr"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "WizType"))
        ////////////////////////////////////////////////////////////////////////////////////////////
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "UseDhcp"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ATICCIDResp"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SignalCSQ"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SignaldBm"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Signalpct"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "NetReg"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "NwCarrier"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "NwTechnology"))
        schema.add(record)

        //Rec 14:Cadix
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FwId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FwVersion"))
        schema.add(record)

        //Rec 15:Csc
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SerialNo"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Release"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Ux300SerialNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Ux300SoftwareVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Ux100SerialNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Ux100SoftwareVersion"))
        schema.add(record)

        //Rec 16:Atos
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwareVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwarePackage"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SixTerminalId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "MACAddress"))
        schema.add(record)

        //Rec 17:CardEase
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "OEMId"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TerminalId"))
        schema.add(record)

        //Rec 18:FrontPanel
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FirmwareVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "KeyPadName"))
        schema.add(record)

        //Rec 19:ChipnPin
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ManufacturerCode"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SerialNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ModelNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SoftwareVersion"))
        schema.add(record)

        //Rec 20:SwissCash
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TermId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FirmwareVersion"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Enabled276"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "EnabledCash"))
        schema.add(record)

        //Rec 21:Display
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "VersionMajor"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "VersionMinor"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "IMXVersionMajor"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "IMXVersionMinor"))
        schema.add(record)

        //Rec 22:Lul
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ListVersion"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FolderNumber"))
        schema.add(record)

        //Rec 23:ContactCard
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FwId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FwVersion"))
        schema.add(record)

        //Rec 24:GLOBALCOM_CONFIG_SERIAL_NUMBER
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SerialNumber"))
        schema.add(record)

        //Rec 25:GLOBALCOM_CONFIG_FIRMWARE_VERSION
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FirmwareVersion"))
        schema.add(record)

        //Rec 26:GlobalCom
        record = Element()
        record.elements.add(Element(24, "SerialNumber", true))
        record.elements.add(Element(35, "FirmwareVersion", true))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TerminalId"))
        schema.add(record)

        //Rec 27:Ingenico
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TerminalId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TrmSwVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "VcsSwVersion"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TerminalSn"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ContactReaderSn"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ClessReaderSn"))
        schema.add(record)

        //Rec 28:Gecr
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwareVersion"))
        schema.add(record)

        //Rec 29:Voucher
        record = Element()
        record.elements.add(Element(DataType.MXDDT_BOOL, "Enabled"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Present"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "NumScans"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "LastScanResult"))
        schema.add(record)

        //Rec 30:CardReader
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Type"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SerialNumber1"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SerialNumber2"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SerialNumber3"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ModelNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwareVersion1"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwareVersion2"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwareVersion3"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwareVersion4"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SoftwareVersion5"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "MID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "OEMID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "StationID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "PA_DSS_Version"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "MACAddress"))
        schema.add(record)

        //Rec 31:Processor
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "DeviceRevision"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "DeviceFamily"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ProgramFlash"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FlexNVM"))
        schema.add(record)

        //Rec 32:CPUBoard
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Revision"))
        record.elements.add(Element(31, "Processor"))
        schema.add(record)

        //Rec 33:GenCardReaderSwElement
        record = Element()
        record.elements.add(Element(DataType.MXDDT_BOOL, "Used"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Desc"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Version"))
        schema.add(record)

        //Rec 34:GenCardReaderComponent
        record = Element()
        record.elements.add(Element(DataType.MXDDT_BOOL, "Used"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Desc"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SerialNumber"))
        record.elements.add(Element(33, "SwElement", true))
        schema.add(record)

        //Rec 35:GenCardReader
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "Type"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ModelNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "MID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "OEMID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "StationID"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "PAA_DSS_Ver"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Version"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "MACAddr"))
        record.elements.add(Element(34, "Component", true))
        schema.add(record)

        //Rec 36:GenericCardReader
        record = Element()
        record.elements.add(Element(35, "CardReader"))
        schema.add(record)

        //Rec 37:SYSINFO
        record = Element()
        record.isChoice = true
        record.elements.add(Element(0, NameLocation::class.simpleName, false, true))
        record.elements.add(Element(1, PciVersion::class.simpleName, false, true))
        record.elements.add(Element(3, MxdFile::class.simpleName, false, true))
        record.elements.add(Element(4, Boot::class.simpleName, false, true))
        record.elements.add(Element(5, Locale::class.simpleName, false, true))
        record.elements.add(Element(6, Currency::class.simpleName, false, true))
        record.elements.add(Element(7, Printer::class.simpleName, false, true))
        record.elements.add(Element(8, CPLD::class.simpleName, false, true))
        record.elements.add(Element(9, UpperLock::class.simpleName, false, true))
        record.elements.add(Element(10, VaultLock::class.simpleName, false, true))
        record.elements.add(Element(11, PSU::class.simpleName, false, true))
        record.elements.add(Element(12, Coin::class.simpleName, false, true))
        record.elements.add(Element(12, Note::class.simpleName, false, true))
        record.elements.add(Element(13, Modem::class.simpleName, false, true))
        record.elements.add(Element(14, Cadix::class.simpleName, false, true))
        record.elements.add(Element(15, Csc::class.simpleName, false, true))
        record.elements.add(Element(16, Atos::class.simpleName, false, true))
        record.elements.add(Element(17, CardEase::class.simpleName, false, true))
        record.elements.add(Element(18, FrontPanel::class.simpleName, false, true))
        record.elements.add(Element(19, ChipnPin::class.simpleName, false, true))
        record.elements.add(Element(20, SwissCash::class.simpleName, false, true))
        record.elements.add(Element(21, Display::class.simpleName, false, true))
        record.elements.add(Element(22, Lul::class.simpleName, false, true))
        record.elements.add(Element(23, ContactCard::class.simpleName, false, true))
        record.elements.add(Element(26, GlobalCom::class.simpleName, false, true))
        record.elements.add(Element(27, Ingenico::class.simpleName, false, true))
        record.elements.add(Element(28, Gecr::class.simpleName, false, true))
        record.elements.add(Element(29, Voucher::class.simpleName, false, true))
        record.elements.add(Element(30, CardReader::class.simpleName, false, true))
        //record.elements.add(Element(31, Processor::class.simpleName, false, true))
        record.elements.add(Element(32, CPUBoard::class.simpleName, false, true))
        record.elements.add(Element(36, GenericCardReader::class.simpleName, false, true))
        schema.add(record)
    }

    private fun writeDataBase(bits: ArrayList<Byte>, fieldName: String?): Boolean {
        val index = findIndex(fieldName)
        if (index < 0) {
            return false
        }
        bits.addAll(write7BitUint(index))
        return true
    }
    override fun writeData(bits: ArrayList<Byte>) {
        for (item in items) {
            if (!writeDataBase(bits, item.javaClass.simpleName)) {
                return
            }

            when (item) {
                is NameLocation -> {
                    bits.addAll(writeString(item.Name))
                    bits.addAll(writeString(item.Location))
                    bits.addAll(writeString(item.LocationId))
                    bits.addAll(writeString(item.SerialNoStr))
                    bits.addAll(write7BitUint(item.UniqueIdentity))
                }
                is PciVersion -> {
                    bits.addAll(writeString(item.SysVer))
                    bits.addAll(write7BitUint(item.SsVer.size))
                    for (ver in item.SsVer) {
                        bits.addAll(write7BitUint(ver))
                    }
                    bits.addAll(write7BitUint(item.SsCRC.size))
                    for (crc in item.SsCRC) {
                        bits.addAll(write7BitUint(crc))
                    }
                }
                is MxdFile -> {
                    bits.addAll(write7BitUint(item.File.FileSize))
                    bits.addAll(write7BitUint(item.File.FileCrc))
                    bits.addAll(writeString(item.File.FileName))
                    bits.addAll(writeString(item.File.Customer))
                    bits.addAll(write7BitUint(item.File.CreationTime))
                    bits.addAll(writeEnum(item.File.ContentType))
                    bits.addAll(writeString(item.File.Version))
                    bits.addAll(write7BitUint(item.File.EncryptionType))
                    bits.addAll(write7BitUint(item.File.ValidFromTime))
                    bits.addAll(write7BitUint(item.File.CompatibilityLevel))
                    bits.addAll(write7BitInt(item.File.CreationTz))
                    bits.addAll(write7BitInt(item.File.ValidFromTz))
                }
                is Boot -> {
                    bits.addAll(writeString(item.Version))
                }
                is Locale -> {
                    bits.addAll(write7BitInt(item.No))
                    bits.addAll(writeString(item.Id))
                    bits.addAll(writeBoolean(item.User))
                    bits.addAll(writeBoolean(item.Maint))
                }
                is Currency -> {
                    bits.addAll(write7BitUint(item.No))
                    bits.addAll(writeEnum(item.Iso4217Code))
                    bits.addAll(write7BitUint(item.ExchangeRate))
                }
                is Printer -> {
                    bits.addAll(writeEnum(item.Type))
                    bits.addAll(write7BitUint(item.FwVersion))
                    bits.addAll(writeString(item.FwVersionStr))
                }
                is CPLD -> {
                    bits.addAll(writeString(item.DesignRef))
                    bits.addAll(writeString(item.Version))
                }
                is UpperLock -> {
                    bits.addAll(writeEnum(item.UpperLockType))
                    bits.addAll(write7BitUint(item.UpperLockFwVersion))
                }
                is VaultLock -> {
                    bits.addAll(writeEnum(item.VaultType))
                    bits.addAll(write7BitUint(item.VaultFwVersion))
                }
                is PSU -> {
                    bits.addAll(writeBoolean(item.ReportWhenMainsOff))
                    bits.addAll(writeBoolean(item.ReportWhenSolarOff))
                    bits.addAll(write7BitUint(item.FwVersion))
                    bits.addAll(write7BitUint(item.BoardIssue))
                }
                is Coin, is Note -> {
                    item as SysinfoCash
                    bits.addAll(writeEnum(item.Type))
                    bits.addAll(writeString(item.FwVersion))
                    bits.addAll(writeString(item.RejFile))
                    bits.addAll(writeString(item.Validator))
                }
                is Modem -> {
                    bits.addAll(writeString(item.Name))
                    bits.addAll(writeEnum(item.Class))
                    bits.addAll(writeBoolean(item.Voice))
                    bits.addAll(write7BitUint(item.No))
                    bits.addAll(writeString(item.ATI2Resp))
                    bits.addAll(writeString(item.ATCGMMResp))
                    bits.addAll(writeString(item.ATCGMIResp))
                    bits.addAll(writeString(item.ATCGMRResp))
                    bits.addAll(writeString(item.ATCGSNResp))
                    bits.addAll(writeString(item.ATiRP0Resp))
                    bits.addAll(writeString(item.ATiRP5Resp))
                    bits.addAll(writeString(item.ATiRP1Resp))
                    bits.addAll(writeString(item.ATiMACAResp))
                    bits.addAll(writeString(item.WizVersion))
                    bits.addAll(writeString(item.WizMacAddr))
                    bits.addAll(writeString(item.WizType))
                    ////////////////////////////////////////////////////////////////////////////////
                    bits.addAll(write7BitUint(item.UseDhcp))
                    bits.addAll(writeString(item.ATICCIDResp))
                    bits.addAll(write7BitUint(item.SignalCSQ))
                    bits.addAll(write7BitUint(item.SignaldBm))
                    bits.addAll(write7BitUint(item.Signalpct))
                    bits.addAll(writeString(item.NetReg))
                    bits.addAll(writeString(item.NwCarrier))
                    bits.addAll(writeString(item.NwTechnology))
                }
                is Cadix -> {
                    bits.addAll(writeString(item.FwId))
                    bits.addAll(writeString(item.FwVersion))
                }
                is Csc -> {
                    bits.addAll(write7BitUint(item.SerialNo))
                    bits.addAll(writeString(item.Release))
                    bits.addAll(writeString(item.Ux300SerialNumber))
                    bits.addAll(writeString(item.Ux300SoftwareVersion))
                    bits.addAll(writeString(item.Ux100SerialNumber))
                    bits.addAll(writeString(item.Ux100SoftwareVersion))
                }
                is Atos -> {
                    bits.addAll(writeString(item.SoftwareVersion))
                    bits.addAll(writeString(item.SoftwarePackage))
                    bits.addAll(writeString(item.SixTerminalId))
                    bits.addAll(writeString(item.MACAddress))
                }
                is CardEase -> {
                    bits.addAll(write7BitUint(item.OEMId))
                    bits.addAll(write7BitUint(item.TerminalId))
                }
                is FrontPanel -> {
                    bits.addAll(write7BitUint(item.FirmwareVersion))
                    bits.addAll(writeString(item.KeyPadName))
                }
                is ChipnPin -> {
                    bits.addAll(writeString(item.ManufacturerCode))
                    bits.addAll(writeString(item.SerialNumber))
                    bits.addAll(writeString(item.ModelNumber))
                    bits.addAll(write7BitUint(item.SoftwareVersion))
                }
                is SwissCash -> {
                    bits.addAll(write7BitUint(item.TermId))
                    bits.addAll(writeString(item.FirmwareVersion))
                    bits.addAll(writeBoolean(item.Enabled276))
                    bits.addAll(writeBoolean(item.EnabledCash))
                }
                is Display -> {
                    bits.addAll(write7BitUint(item.VersionMajor))
                    bits.addAll(write7BitUint(item.VersionMinor))
                    bits.addAll(write7BitUint(item.IMXVersionMajor))
                    bits.addAll(write7BitUint(item.IMXVersionMinor))
                }
                is Lul -> {
                    bits.addAll(writeString(item.ListVersion))
                    bits.addAll(write7BitUint(item.FolderNumber))
                }
                is ContactCard -> {
                    bits.addAll(writeString(item.FwId))
                    bits.addAll(writeString(item.FwVersion))
                }
                is GlobalCom -> {
                    for (sn in item.SerialNumber) {
                        bits.addAll(writeString(sn.SerialNumber))
                    }
                    for (fv in item.FirmwareVersion) {
                        bits.addAll(writeString(fv.FirmwareVersion))
                    }
                    bits.addAll(writeString(item.TerminalId))
                }
                is Ingenico -> {
                    bits.addAll(writeString(item.TerminalId))
                    bits.addAll(writeString(item.TrmSwVersion))
                    bits.addAll(writeString(item.VcsSwVersion))
                    bits.addAll(writeString(item.TerminalSn))
                    bits.addAll(writeString(item.ContactReaderSn))
                    bits.addAll(writeString(item.ClessReaderSn))
                }
                is Gecr -> {
                    bits.addAll(writeString(item.SoftwareVersion))
                }
                is Voucher -> {
                    bits.addAll(writeBoolean(item.Enabled))
                    bits.addAll(writeBoolean(item.Present))
                    bits.addAll(write7BitInt(item.NumScans))
                    bits.addAll(writeString(item.LastScanResult))
                }
                is CardReader -> {
                    bits.addAll(writeString(item.Type))
                    bits.addAll(writeString(item.SerialNumber1))
                    bits.addAll(writeString(item.SerialNumber2))
                    bits.addAll(writeString(item.SerialNumber3))
                    bits.addAll(writeString(item.ModelNumber))
                    bits.addAll(writeString(item.SoftwareVersion1))
                    bits.addAll(writeString(item.SoftwareVersion2))
                    bits.addAll(writeString(item.SoftwareVersion3))
                    bits.addAll(writeString(item.SoftwareVersion4))
                    bits.addAll(writeString(item.SoftwareVersion5))
                    bits.addAll(writeString(item.TID))
                    bits.addAll(writeString(item.MID))
                    bits.addAll(writeString(item.OEMID))
                    bits.addAll(writeString(item.StationID))
                    bits.addAll(writeString(item.PA_DSS_Version))
                    bits.addAll(writeString(item.MACAddress))
                }
                is CPUBoard -> {
                    bits.addAll(writeString(item.Revision))
                    bits.addAll(write7BitUint(item.Processor.DeviceRevision))
                    bits.addAll(writeString(item.Processor.DeviceFamily))
                    bits.addAll(writeString(item.Processor.ProgramFlash))
                    bits.addAll(writeString(item.Processor.FlexNVM))
                }
                is GenericCardReader -> {
                    item.CardReader.also {
                        bits.addAll(writeEnum(it.Type))
                        bits.addAll(writeString(it.ModelNumber))
                        bits.addAll(writeString(it.TID))
                        bits.addAll(writeString(it.MID))
                        bits.addAll(writeString(it.OEMID))
                        bits.addAll(writeString(it.StationID))
                        bits.addAll(writeString(it.PAA_DSS_Ver))
                        bits.addAll(writeString(it.Version))
                        bits.addAll(writeString(it.MACAddr))
                        bits.addAll(write7BitUint(it.Component.size))
                        for (comp in it.Component) {
                            bits.addAll(writeBoolean(comp.Used))
                            bits.addAll(writeString(comp.Desc))
                            bits.addAll(writeString(comp.SerialNumber))
                            bits.addAll(write7BitUint(comp.SwElement.size))
                            for (el in comp.SwElement) {
                                bits.addAll(writeBoolean(el.Used))
                                bits.addAll(writeString(el.Desc))
                                bits.addAll(writeString(el.Version))
                            }
                        }
                    }
                }
            }
        }
        bits.add(0.toByte())
    }

    fun addNameLocation(Name: String, Location: String, LocationId: String, SerialNoStr: String) {
        val item = NameLocation()
        item.Name = Name
        item.Location = Location
        item.LocationId = LocationId
        item.SerialNoStr = SerialNoStr.replace("_", "").filter { it.isLetterOrDigit() }.uppercase()
        item.UniqueIdentity = header.machineUniqueID
        addItem(item)
    }

    @Suppress("unused")
    fun addPciVersion(SysVer: String, SsVer: List<Int>, SsCRC: List<Long>) {
        val item = PciVersion()
        item.SysVer = SysVer
        for (ver in SsVer) {
            item.SsVer.add(ver)
        }
        for (crc in SsCRC) {
            item.SsCRC.add(crc)
        }
        addItem(item)
    }

    @Suppress("unused")
    fun addMxdFile(file: File) {
        val entry = FileMxdUtils.file2Entry(file) ?: return
        addMxdFile(entry)
    }
    fun addMxdFile(entry: Entry = Entry()) {
        val item = MxdFile()
        item.File.setFile(entry)
        addItem(item)
    }
    @Suppress("unused")
    fun addMxdFile(
        FileSize: Long,
        FileCrc: Long,
        FileName: String,
        Customer: String,
        CreationTime: Long,
        ContentType: MxdContentTypeEnum,
        Version: String,
        EncryptionType: Int,
        ValidFromTime: Long,
        CompatibilityLevel: Int,
        CreationTz: Int,
        ValidFromTz: Int,
    ) {
        val entry = Entry()
        entry.FileSize = FileSize
        entry.FileCrc = FileCrc
        entry.FileName = FileName
        entry.Customer = Customer
        entry.CreationTime = CreationTime
        entry.ContentType = ContentType
        entry.Version = Version
        entry.EncryptionType = EncryptionType
        entry.ValidFromTime = ValidFromTime
        entry.CompatibilityLevel = CompatibilityLevel
        entry.CreationTz = CreationTz
        entry.ValidFromTz = ValidFromTz
        addMxdFile(entry)
    }

    fun addBoot(Version: String) {
        val item = Boot()
        item.Version = Version
        addItem(item)
    }

    fun addLocale(No: Int, Id: String, User: Boolean, Maint: Boolean) {
        val item = Locale()
        item.No = No
        item.Id = Id
        item.User = User
        item.Maint = Maint
        addItem(item)
    }

    fun addCurrency(No: Int, Iso4217Code: CurrencyIso4217Enum, ExchangeRate: Int) {
        val item = Currency()
        item.No = No
        item.Iso4217Code = Iso4217Code
        item.ExchangeRate = ExchangeRate
        addItem(item)
    }

    @Suppress("unused")
    fun addPrinter(Type: PrinterTypeEnum, FwVersion: Int, FwVersionStr: String) {
        val item = Printer()
        item.Type = Type
        item.FwVersion = FwVersion
        item.FwVersionStr = FwVersionStr
        addItem(item)
    }

    fun addCPLD(DesignRef: String, Version: String) {
        val item = CPLD()
        //20231129,IO板固件版本号的t，有些是大写，有些是小写？我们把它统一转换成大写。
        item.DesignRef = DesignRef.uppercase()
        item.Version = Version.uppercase()
        addItem(item)
    }

    fun addUpperLock(UpperLockType: LMCUlockTypeEnum, UpperLockFwVersion: Int) {
        val item = UpperLock()
        item.UpperLockType = UpperLockType
        item.UpperLockFwVersion = UpperLockFwVersion
        addItem(item)
    }

    fun addVaultLock(VaultType: LMCVaultTypeEnum, VaultFwVersion: Int) {
        val item = VaultLock()
        item.VaultType = VaultType
        item.VaultFwVersion = VaultFwVersion
        addItem(item)
    }

    fun addPSU(ReportWhenMainsOff: Boolean, ReportWhenSolarOff: Boolean, FwVersion: Int, BoardIssue: Int) {
        val item = PSU()
        item.ReportWhenMainsOff = ReportWhenMainsOff
        item.ReportWhenSolarOff = ReportWhenSolarOff
        item.FwVersion = FwVersion
        item.BoardIssue = BoardIssue
        addItem(item)
    }

    fun addCoin(Type: CurrencyInfo, FwVersion: String, RejFile: String = Default_RejFile, Validator: String = Default_Validator) {
        addCash(Coin::class.simpleName, Type, FwVersion, RejFile, Validator)
    }
    @Suppress("unused")
    fun addNote(Type: CurrencyInfo, FwVersion: String, RejFile: String = Default_RejFile, Validator: String = Default_Validator) {
        addCash(Note::class.simpleName, Type, FwVersion, RejFile, Validator)
    }
    fun addCash(className: String?, Type: CurrencyInfo, FwVersion: String, RejFile: String = Default_RejFile, Validator: String = Default_Validator) {
        val item = when (className) {
            Coin::class.simpleName -> {
                Coin()
            }
            Note::class.simpleName -> {
                Note()
            }
            else -> {
                return
            }
        }
        item.Type = Type
        item.FwVersion = FwVersion
        item.RejFile = RejFile
        item.Validator = Validator
        addItem(item)
    }

    //新西兰新增需求，增加字段，弃用该接口，改用addItem
//    fun addModem(Name: String,
//                 Class: ModemClassEnum,
//                 Voice: Boolean,
//                 No: Int,
//                 ATI2Resp: String,
//                 ATCGMMResp: String,
//                 ATCGMIResp: String,
//                 ATCGMRResp: String,
//                 ATCGSNResp: String,
//                 ATiRP0Resp: String,
//                 ATiRP5Resp: String,
//                 ATiRP1Resp: String,
//                 ATiMACAResp: String,
//                 WizVersion: String,
//                 WizMacAddr: String,
//                 WizType: String) {
//        val item = Modem()
//        item.Name = Name
//        item.Class = Class
//        item.Voice = Voice
//        item.No = No
//        item.ATI2Resp = ATI2Resp
//        item.ATCGMMResp = ATCGMMResp
//        item.ATCGMIResp = ATCGMIResp
//        item.ATCGMRResp = ATCGMRResp
//        item.ATCGSNResp = ATCGSNResp
//        item.ATiRP0Resp = ATiRP0Resp
//        item.ATiRP5Resp = ATiRP5Resp
//        item.ATiRP1Resp = ATiRP1Resp
//        item.ATiMACAResp = ATiMACAResp
//        item.WizVersion = WizVersion
//        item.WizMacAddr = WizMacAddr
//        item.WizType = WizType
//        addItem(item)
//    }

    @Suppress("unused")
    fun addCadix(FwId: String, FwVersion: String) {
        val item = Cadix()
        item.FwId = FwId
        item.FwVersion = FwVersion
        addItem(item)
    }

    @Suppress("unused")
    fun addCsc(SerialNo: Long = 0,
               Release: String = "",
               Ux300SerialNumber: String = "",
               Ux300SoftwareVersion: String = "",
               Ux100SerialNumber: String = "",
               Ux100SoftwareVersion: String = "") {
        val item = Csc()
        //VAR_INT64
        item.SerialNo = SerialNo
        item.Release = Release
        item.Ux300SerialNumber = Ux300SerialNumber
        item.Ux300SoftwareVersion = Ux300SoftwareVersion
        item.Ux100SerialNumber = Ux100SerialNumber
        item.Ux100SoftwareVersion = Ux100SoftwareVersion
        addItem(item)
    }

    @Suppress("unused")
    fun addAtos(SoftwareVersion: String,
                SoftwarePackage: String,
                SixTerminalId: String,
                MACAddress: String) {
        val item = Atos()
        item.SoftwareVersion = SoftwareVersion
        item.SoftwarePackage = SoftwarePackage
        item.SixTerminalId = SixTerminalId
        item.MACAddress = MACAddress
        addItem(item)
    }

    @Suppress("unused")
    fun addCardEase(OEMId: Int = 9997, TerminalId: Int = 0) {
        val item = CardEase()
        item.OEMId = OEMId
        item.TerminalId = TerminalId
        addItem(item)
    }

    @Suppress("unused")
    fun addFrontPanel(FirmwareVersion: Int, KeyPadName: String = "") {
        val item = FrontPanel()
        item.FirmwareVersion = FirmwareVersion
        item.KeyPadName = KeyPadName
        addItem(item)
    }

    @Suppress("unused")
    fun addChipnPin(ManufacturerCode: String, SerialNumber: String, ModelNumber: String, SoftwareVersion: Int) {
        val item = ChipnPin()
        item.ManufacturerCode = ManufacturerCode
        item.SerialNumber = SerialNumber
        item.ModelNumber = ModelNumber
        item.SoftwareVersion = SoftwareVersion
        addItem(item)
    }

    @Suppress("unused")
    fun addSwissCash(TermId: Long, FirmwareVersion: String, Enabled276: Boolean, EnabledCash: Boolean) {
        val item = SwissCash()
        item.TermId = TermId
        item.FirmwareVersion = FirmwareVersion
        item.Enabled276 = Enabled276
        item.EnabledCash = EnabledCash
        addItem(item)
    }

    @Suppress("unused")
    fun addDisplay(VersionMajor: Int, VersionMinor: Int, IMXVersionMajor: Int, IMXVersionMinor: Int) {
        val item = Display()
        item.VersionMajor = VersionMajor
        item.VersionMinor = VersionMinor
        item.IMXVersionMajor = IMXVersionMajor
        item.IMXVersionMinor = IMXVersionMinor
        addItem(item)
    }

    @Suppress("unused")
    fun addLul(ListVersion: String, FolderNumber: Int) {
        val item = Lul()
        item.ListVersion = ListVersion
        item.FolderNumber = FolderNumber
        addItem(item)
    }

    @Suppress("unused")
    fun addContactCard(FwId: String, FwVersion: String) {
        val item = ContactCard()
        item.FwId = FwId
        item. FwVersion = FwVersion
        addItem(item)
    }

    @Suppress("unused")
    fun addGlobalCom(SerialNumber: List<String>, FirmwareVersion: List<String>, TerminalId: String) {
        val item = GlobalCom()
        for (sn in SerialNumber) {
            val gcsn = GLOBALCOM_CONFIG_SERIAL_NUMBER()
            gcsn.SerialNumber = sn
            item.SerialNumber.add(gcsn)
        }
        for (fv in FirmwareVersion) {
            val gcfv = GLOBALCOM_CONFIG_FIRMWARE_VERSION()
            gcfv.FirmwareVersion = fv
            item.FirmwareVersion.add(gcfv)
        }
        item.TerminalId = TerminalId
        addItem(item)
    }

    @Suppress("unused")
    fun addIngenico(TerminalId: String,
                    TrmSwVersion: String,
                    VcsSwVersion: String,
                    TerminalSn: String,
                    ContactReaderSn: String,
                    ClessReaderSn: String) {
        val item = Ingenico()
        item.TerminalId = TerminalId
        item.TrmSwVersion = TrmSwVersion
        item.VcsSwVersion = VcsSwVersion
        item.TerminalSn = TerminalSn
        item.ContactReaderSn = ContactReaderSn
        item.ClessReaderSn = ClessReaderSn
        addItem(item)
    }

    @Suppress("unused")
    fun addGecr(SoftwareVersion: String) {
        val item = Gecr()
        item.SoftwareVersion = SoftwareVersion
        addItem(item)
    }

    @Suppress("unused")
    fun addVoucher(Enabled: Boolean, Present: Boolean, NumScans: Int, LastScanResult: String) {
        val item = Voucher()
        item.Enabled = Enabled
        item.Present = Present
        item.NumScans = NumScans
        item.LastScanResult = LastScanResult
        addItem(item)
    }

    @Suppress("unused")
    fun addCardReader(Type: String,
                      SerialNumber1: String,
                      SerialNumber2: String,
                      SerialNumber3: String,
                      ModelNumber: String,
                      SoftwareVersion1: String,
                      SoftwareVersion2: String,
                      SoftwareVersion3: String,
                      SoftwareVersion4: String,
                      SoftwareVersion5: String,
                      TID: String,
                      MID: String,
                      OEMID: String,
                      StationID: String,
                      PA_DSS_Version: String,
                      MACAddress: String) {
        val item = CardReader()
        item.Type = Type
        item.SerialNumber1 = SerialNumber1
        item.SerialNumber2 = SerialNumber2
        item.SerialNumber3 = SerialNumber3
        item.ModelNumber = ModelNumber
        item.SoftwareVersion1 = SoftwareVersion1
        item.SoftwareVersion2 = SoftwareVersion2
        item.SoftwareVersion3 = SoftwareVersion3
        item.SoftwareVersion4 = SoftwareVersion4
        item.SoftwareVersion5 = SoftwareVersion5
        item.TID = TID
        item.MID = MID
        item.OEMID = OEMID
        item.StationID = StationID
        item.PA_DSS_Version = PA_DSS_Version
        item.MACAddress = MACAddress
        addItem(item)
    }

    fun addGenericCardReader(genInfo: GenericCardReader) {
        addItem(genInfo)
    }

    @Suppress("unused")
    fun addCPUBoard(Revision: String = "E", Processor: Processor) {
        val item = CPUBoard()
        item.Revision = Revision
        item.Processor = Processor
        addItem(item)
    }

    @Suppress("unused")
    class SYSINFO {
        val NameLocation = NameLocation()
        val PciVersion = PciVersion()
        val MxdFile = MxdFile()
        val Boot = Boot()
        val Locale = Locale()
        val Currency = Currency()
        val Printer = Printer()
        val CPLD = CPLD()
        val UpperLock = UpperLock()
        val VaultLock = VaultLock()
        val PSU = PSU()
        val Coin = Coin()
        val Note = Note()
        val Modem = Modem()
        val Cadix = Cadix()
        val Csc = Csc()
        val Atos = Atos()
        val CardEase = CardEase()
        val FrontPanel = FrontPanel()
        val ChipnPin = ChipnPin()
        val SwissCash = SwissCash()
        val Display = Display()
        val Lul = Lul()
        val ContactCard = ContactCard()
        val GlobalCom = GlobalCom()
        val Ingenico = Ingenico()
        val Gecr = Gecr()
        val Voucher = Voucher()
        val CardReader = CardReader()
        val CPUBoard = CPUBoard()
    }
}
