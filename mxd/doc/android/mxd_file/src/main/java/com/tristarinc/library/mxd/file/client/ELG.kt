package com.tristarinc.library.mxd.file.client

import android.annotation.SuppressLint
import android.os.SystemClock
import android.util.Base64
import com.tristarinc.library.gson.JsonUtils
import com.tristarinc.library.interfaces.base.FlagLevelEnum
import com.tristarinc.library.kotlin.runThread
import com.tristarinc.library.language.Languages
import com.tristarinc.library.mlog.MLog
import com.tristarinc.library.mxd.bean.DataType
import com.tristarinc.library.mxd.bean.Element
import com.tristarinc.library.mxd.bean.FileType
import com.tristarinc.library.mxd.bean.Header
import com.tristarinc.library.mxd.file.FileMxdUtils
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.bean.Entry
import com.tristarinc.library.mxd.file.enums.*
import com.tristarinc.library.mxd.file.server.BOC
import com.tristarinc.library.sqlite.SQLiteManager
import java.io.File
import java.time.Instant
import java.util.Hashtable
import java.util.Vector

@Suppress("PropertyName", "unused")
class ELG(origin: String, machineUniqueID: Long) : MXD() {

    init {
        create(FileType.ELG, origin, machineUniqueID)
    }

    @Suppress("ClassName")
    companion object {

        private const val SQLITE_TABLE_NAME = "elg"

        class SQLiteELG {
            var id = 0
            var json = ""
            var className = ""
        }
        ////////////////////////////////////////////////////////////////////////////////////////////

        var nextSequenceNum = 0L

        open class ElgEntry {
            val Time = Instant.now().epochSecond
            var SequenceNumber = 0L
            fun newSequenceNumber() {
                SequenceNumber = nextSequenceNum ++
            }
        }

        class OfflineFileTransferStart : ElgEntry()

        class Startup : ElgEntry() {
            var StartupReason = StartupReasonEnum.UNKNOWN
            //-32768~32767
            //VAR_INT64
            var AccumulatorVoltage = 0
        }

        class ExceptionPostmortem : ElgEntry() {
            var CrashReason = CrashReasonEnum.UNKNOWN
            val Registers = ArrayList<Long>()
            var Psr = 0L
            var Task = 0L
            var TaskStackStart = 0L
            var TaskStackEnd = 0L
            var TaskName = ""
        }

        class ExceptionStackDump: ElgEntry() {
            var ExceptionType = ""
            var Message = ""
            var StackTrace = ""
        }

        class StatusFlagChange : ElgEntry() {
            var Set = false
            var Dev = 0
            var Flag = 0
            var Level = FlagLevelEnum.E
            var DevDesc = ""
                set(value) {
                    field = value.take(31)
                }
            var FlagDesc = ""
                set(value) {
                    field = value.take(31)
                }
        }

        class Transaction : ElgEntry() {
            var TransactionType = TransactionTypeEnum.DEBIT
            var TransactionSerialNumber = 0L
            var AmountCharged = 0L
            var AmountPaid = 0L
            var TariffCode = ""
            var StartTime = 0L
            var EndTime = 0L
            var RegistrationNumber = ""
            var SpaceNumber = 0L
            var ZoneId = 0L
            var VrmSelected = VrmSelectTypeEnum.ANPR
            var ConcessionEntered = ConcessionEnteredTypeEnum.SCANNED
            var ConcessionCode = ""
            var LoyaltyID = ""
        }

        class OtherTransaction: ElgEntry() {
            var TransactionSerialNumber = 0L
            var TransactionType = TransactionTypes.FinePayment
            var AmountCharged = 0L
            var TransactionTime = 0L
            var ForeignId = ""
            var RegistrationNumber = ""
            var CardDetails = ArrayList<PaymentCardDetails>()
            var CashDetails = ArrayList<PaymentCashDetails>()

            enum class TransactionTypes {
                FinePayment, Other;
            }

            class PaymentCardDetails {
                var CardNumber = ""
                var CardType = ""
                var TransactionReference = ""
                var Iso4217Code = CurrencyIso4217Enum.GBP
                var AuthorisationCode = ""
                var AmountPaid = 0L
                var TerminalId = ""
            }

            class PaymentCashDetails {
                var CashType = CashTypes.COIN
                var Iso4217Code = CurrencyIso4217Enum.GBP
                var AmountPaid = 0L

                enum class CashTypes {
                    COIN, NOTE;
                }
            }
        }

        class VESCatSelect : ElgEntry() {
            var TransactionSerialNumber = 0L
            var RegistrationNumber = ""
            var SelectedTariffCategoryRule = ""
            var AmountPaid = 0L
            var VesResult = VESResult()

            class VESResult {
                var VesResponse = VESResponse()

                class VESResponse {
                    var HTTPStatus = 0
                    var FuelType = ""
                    var Co2 = 0
                    var EngineCC = 0
                    var ErrorDesc = ""
                }

                var SelectionReason = ""
            }
        }

        class TransportTransaction : ElgEntry() {
            var TransactionSerialNumber = 0L
            var AmountCharged = 0L
            var StartTime = 0L
            var EndTime = 0L
            var NumberOfPassengers = 0
            var TariffCode = ""
        }

        class CardNonPayment : ElgEntry() {
            var TransactionSerialNumber = 0L
            var CardType = CardSystemTypesEnum.UNKNOWN
            var CardNumber = ""
            var Status = CardProcessStatusEnum.FAILED
        }

        open class EVENT_LOG_AUDIT_CARD_DEBIT : ElgEntry() {
            var TransactionSerialNumber = 0L
            var CardType = CardSystemTypesEnum.UNKNOWN
            var CardNumber = ""
            var Iso4217Code = CurrencyIso4217Enum.GBP
            var AuthorisationCode = ""
            var Status = CardProcessStatusEnum.FAILED
            var AmountPaid = 0L
            var Balance = 0L
            var TerminalId = ""
            var LoyaltyID = ""
        }
        class CardDebit: EVENT_LOG_AUDIT_CARD_DEBIT()
        class CardUnrefunded: EVENT_LOG_AUDIT_CARD_DEBIT()

        open class EVENT_LOG_AUDIT_CARD_CREDIT_REFUND : ElgEntry() {
            var TransactionSerialNumber = 0L
            var CardType = CardSystemTypesEnum.UNKNOWN
            var CardNumber = ""
            var Iso4217Code = CurrencyIso4217Enum.GBP
            var AuthorisationCode = ""
            var Status = CardProcessStatusEnum.FAILED
            var AmountCredited = 0L
            var Balance = 0L
            var TerminalId = ""
            var LoyaltyID = ""
        }

        class CardCredit : EVENT_LOG_AUDIT_CARD_CREDIT_REFUND()
        class CardRefund : EVENT_LOG_AUDIT_CARD_CREDIT_REFUND()

        open class EVENT_LOG_AUDIT_CASH_TRANS : ElgEntry() {
            var TransactionSerialNumber = 0L
            var AmountPaid = 0L
        }

        class CoinDebit : EVENT_LOG_AUDIT_CASH_TRANS()
        class NoteDebit : EVENT_LOG_AUDIT_CASH_TRANS()
        class CoinUnrefunded : EVENT_LOG_AUDIT_CASH_TRANS()
        class NoteUnrefunded : EVENT_LOG_AUDIT_CASH_TRANS()

        class AUDIT_TOKEN_TRANS_INFO {
            var AmountPaid = 0L
            var TokenChannelId = ""
        }

        class TokenDebit : ElgEntry() {
            var TransactionSerialNumber = 0L
            var AmountPaid = 0L
            val TokenInfo = ArrayList<AUDIT_TOKEN_TRANS_INFO>()
        }

        class KeyPresented : ElgEntry() {
            //VAR_INT64
            var KeyNumber = 0L
            var KeyType = DKMKeyTypeEnum.UNKNOWN
            var Accepted = false
            var PresentationTime = 0L
            var SerialNo = 0L
            var Name = ""
        }

        class TicketStock : ElgEntry() {
            var Printer = TicketPrinterEnum.LEFT
            var TimeChanged = 0L
            var OldRollLength = 0L
            var TicketsUsed = 0L
            var NewRollLength = 0L
        }

        class CardCollection : ElgEntry() {
            var TriggerType = EndAuditPeriodEnum.BACK_OFFICE_REQUEST
            var CardType = CardSystemTypesEnum.UNKNOWN
        }

        class AUDIT_CASH_PERIOD_ITEM {
            var Iso4217Code = CurrencyIso4217Enum.GBP
            var Denomination = 0
            var Count = 0L
            var UnrefundedCount = 0L
        }

        class AUDIT_CASH_PERIOD_GRAND_TOTAL {
            var Iso4217Code = CurrencyIso4217Enum.GBP
            var DecimalPlaces = 2
            var GrandTotalAtLastCashBoxPull = 0L
            var UnrefundedAtLastCashBoxPull = 0L
        }

        class AUDIT_CASH_PERIOD {
            var CashboxPullNumber = 0L
            var StartTime = 0L
            var EndTime = 0L
            var Transactions = 0L
            var Volume = 0L
            var Value = 0L
            var nItems = 0
            var nCurrencyGrandTotals = 0
            val Item = ArrayList<AUDIT_CASH_PERIOD_ITEM>()
            val CurrencyGrandTotal = ArrayList<AUDIT_CASH_PERIOD_GRAND_TOTAL>()
            var UnRefundedTransactions = 0L
            var CumTotalTransactions = 0L
        }

        class CashBoxRemoved : ElgEntry() {
            var BoxType = BoxTypeEnum.COIN
            var Data = AUDIT_CASH_PERIOD()
        }

        class AUDIT_CARD_SYSTEM {
            var CardType = CardSystemTypesEnum.UNKNOWN
            var DebitTransactions = 0L
            var DebitAmount = 0L
            var CreditTransactions = 0L
            var CreditAmount = 0L
            var RefundedAmount = 0L
            var UnRefundedAmount = 0L
        }

        class AUDIT_CARD_PERIOD {
            var AuditNo = 0L
            var StartTime = 0L
            var EndTime = 0L
            var CumDebitTransactions = 0L
            var CumDebitAmount = 0L
            var CumCreditTransactions = 0L
            var CumCreditAmount = 0L
            val CardSystem = ArrayList<AUDIT_CARD_SYSTEM>()
        }

        class CardAuditPeriodEnd : ElgEntry() {
            var TriggerType = EndAuditPeriodEnum.COIN_BOX_WITHDRAWAL
            var TriggerSequenceNumber = 0L
            val Data = AUDIT_CARD_PERIOD()
        }

        class AUDIT_TRANSACTION_TIMEBAND_AMOUNTS2 {
            var A = 0L
            var B = 0L
            var C = 0L
        }

        class AUDIT_TRANSACTION_TIMEBAND_AMOUNTS {
            val NoFreeTimeInterval = AUDIT_TRANSACTION_TIMEBAND_AMOUNTS2()
            val FreeTimeInterval = AUDIT_TRANSACTION_TIMEBAND_AMOUNTS2()
            val TicketsValue = AUDIT_TRANSACTION_TIMEBAND_AMOUNTS2()
        }

        class AUDIT_TRANSACTION_CATEGORY_AMOUNTS {
            var TotalAmount = 0L
            var TotalTickets = 0L
            var TotalFreeTickets = 0L
        }

        class AUDIT_TRANSACTION_PERIOD {
            var AuditNo = 0L
            var StartTime = 0L
            var EndTime = 0L
            var DebitTransactions = 0L
            var CreditTransactions = 0L
            val TimeBands = ArrayList<AUDIT_TRANSACTION_TIMEBAND_AMOUNTS>()
            val Categories = ArrayList<AUDIT_TRANSACTION_CATEGORY_AMOUNTS>()
            var TotalCreditAmount = 0L
        }

        class TransactionAuditPeriodEnd : ElgEntry() {
            var TriggerType = EndAuditPeriodEnum.COIN_BOX_WITHDRAWAL
            var TriggerSequenceNumber = 0L
            var Data = AUDIT_TRANSACTION_PERIOD()
        }

        class AUDIT_SPACE_SYSTEM_ZONE {
            var ZoneId = 0L
            var TotalTransaction = 0L
            var TotalAmountPaid = 0L
            var TotalAmountCharged = 0L
        }

        class AUDIT_SPACE_SYSTEM_PERIOD {
            var AuditNo = 0L
            var StartTime = 0L
            var EndTime = 0L
            var nZones = 0
            val Zones = ArrayList<AUDIT_SPACE_SYSTEM_ZONE>()
        }

        class SpaceSystemAuditPeriodEnd : ElgEntry() {
            var TriggerType = EndAuditPeriodEnum.COIN_BOX_WITHDRAWAL
            var TriggerSequenceNumber = 0L
            val Data = AUDIT_SPACE_SYSTEM_PERIOD()
        }

        class TmsCall : ElgEntry() {
            var CardReaderType = ""
            var StartTime = 0L
            var Duration = 0L
            var Status = CardProcessStatusEnum.FAILED
        }

        class RechargeLimitChange : ElgEntry() {
            var Expiry = 0L
            var Quantity = 0L
        }

        class TestToken : ElgEntry() {
            var Action = TokenActionEnum.ERROR
        }

        class Lock : ElgEntry() {
            var LockType = LMCLockTypeEnum.UPPER_LOCK
            var KeyPresentationTime = 0L
            //VAR_INT64
            var KeyNumber = 0L
            var Succeeded = false
            var LockStatus = LMCLockStatusEnum.LOCK_STATUS_UNKNOWN
        }

        class PSU_STATISTICS_AV_MIN_MAX {
            //VAR_INT64
            var Average = 0
            //VAR_INT64
            var Min = 0
            //VAR_INT64
            var Max = 0

            fun setValue(value: PSU_STATISTICS_AV_MIN_MAX) {
                this.Average = value.Average
                this.Min = value.Min
                this.Max = value.Max
            }
        }

        class EVENT_LOG_PSU_ACCUMULATOR {
            val CurrentAcc = PSU_STATISTICS_AV_MIN_MAX()
            val VoltageAcc = PSU_STATISTICS_AV_MIN_MAX()
            val Temperature = PSU_STATISTICS_AV_MIN_MAX()

            fun setValue(value: EVENT_LOG_PSU_ACCUMULATOR) {
                this.CurrentAcc.setValue(value.CurrentAcc)
                this.VoltageAcc.setValue(value.VoltageAcc)
                this.Temperature.setValue(value.Temperature)
            }
        }

        class PsuStatistics : ElgEntry() {
            var SampleCount = 0
            var MainsOnSampleCount = 0
            var SolarOnSampleCount = 0
            val TempCurrentAcc = PSU_STATISTICS_AV_MIN_MAX()
            val TempVoltageAcc = PSU_STATISTICS_AV_MIN_MAX()
            val TempTemperature = PSU_STATISTICS_AV_MIN_MAX()
            val Accumulator1 = EVENT_LOG_PSU_ACCUMULATOR()
            val Accumulator2 = EVENT_LOG_PSU_ACCUMULATOR()
        }

        class TEMP_PSU_ACCUMULATOR {
            //0~65535
            var VoltageAcc = 0
            //-32768~32767
            var CurrentAcc = 0
            //-128~127
            var Temperature = 0
            var AccState = AccStateEnum.UNKNOWN
            var ChargeState = AccChargeStateEnum.OFF
            //0~65535
            var LastReadVoltageAcc = 0
            var NewAccState = AccStateEnum.UNKNOWN
            var nDischargeReadings = 0
            var AccumulatorNo = 1
            var Missing = false
            //0~65535
            var VoltageAccMV = 0
            //-32768~32767
            var CurrentAccMA = 0
        }

        class TEMP_PSU_EXT {
            //0~255
            var PsuState = 0
            //0~65535
            var SupplyVoltage = 0
            //0~65535
            var SupplyCurrent = 0
            //0~255
            var FwVersion = 0
            //0~255
            var BoardIssue = 0
            //0~65535
            var SystemFlags = 0
            //0~65535
            var SystemStatus = 0
            //0~255
            var ALT_Status_0 = 0
            var Solar = false
            var Mains = false
            val Accumulator1 = TEMP_PSU_ACCUMULATOR()
            val Accumulator2 = TEMP_PSU_ACCUMULATOR()
            //0~65535
            var SupplyVoltageMV = 0
            //0~65535
            var SupplyCurrentMA = 0
            var ChargerState = PsuMonPicSelectEnum.UNKNOWN
            //0~65535
            var ChargerVoltageMV = 0
            //0~65535
            var SolarVoltageMV = 0
            //0~65535
            var SolarCurrentMA = 0
            //0~65535
            var SolarOCVoltageMV = 0
            //0~65535
            var SleepCurrentMA = 0
            //0~65535
            var SolarSCCurrentMA = 0
            //-128~127
            var BoardTemperature = 0
            //0~255
            var BatteryMode = 0.toByte()
            var PrinterOn = false
            var ExtraTempSensors = false
            var DataValid = PsuMonDataValidEnum.PSU_UNKNOWN
            var A1 = PsuMonPicStatusEnum.UNKNOWN
            var B1 = PsuMonPicStatusEnum.UNKNOWN
            var C1 = PsuMonPicStatusEnum.UNKNOWN
            var D1 = PsuMonPicStatusEnum.UNKNOWN
            var E1 = PsuMonPicStatusEnum.UNKNOWN
            var F1 = PsuMonPicStatusEnum.UNKNOWN
            var A2 = PsuMonPicSelectEnum.UNKNOWN
            var B2 = PsuMonPicSelectEnum.UNKNOWN
            var C2 = PsuMonPicSelectEnum.UNKNOWN
            var D2 = PsuMonPicSelectEnum.UNKNOWN
            var E2 = PsuMonPicSelectEnum.UNKNOWN
            var F2 = PsuMonPicSelectEnum.UNKNOWN
        }

        class PsuStatus : ElgEntry() {
            var Status = TEMP_PSU_EXT()
        }

        open class EVENT_LOG_MXD_SINGLE_FILE : ElgEntry() {
            var File = Entry()
        }
        class APP : EVENT_LOG_MXD_SINGLE_FILE()
        class CFG : EVENT_LOG_MXD_SINGLE_FILE()
        class TRF : EVENT_LOG_MXD_SINGLE_FILE()
        class DKL : EVENT_LOG_MXD_SINGLE_FILE()
        class HTL : EVENT_LOG_MXD_SINGLE_FILE()
        class CLT : EVENT_LOG_MXD_SINGLE_FILE()
        class PIC : EVENT_LOG_MXD_SINGLE_FILE()
        class BL3 : EVENT_LOG_MXD_SINGLE_FILE()
        class LUL : EVENT_LOG_MXD_SINGLE_FILE()

        class BACK_OFFICE_CMD {
            var SerialNo = 0L
            var Command = BackOfficeCmdEnum.UNDEFINED
            var NumberPar1 = 0L
            var StringPar1 = ""
        }

        class BackOfficeCmd : ElgEntry() {
            val Data = BACK_OFFICE_CMD()
        }

        class BACK_OFFICE_RESP {
            var SerialNo = 0L
            var Response = BackOfficeRespEnum.SUCCESS
        }

        class BackOfficeResp : ElgEntry() {
            val Data = BACK_OFFICE_RESP()
        }

        class CallReason : ElgEntry() {
            var SessionSerialNo = 0L
            var ApplicationStart = false
            var StatusFlagChange = false
            var ScheduledCall = false
            var BackOfficeCall = false
            var RetryAfterBusy = false
            var RetryAfterFailure = false
            var TestCall = false
            var ForcedCall = false
            var ImmediateJob = false
        }

        class PenaltyTransaction : ElgEntry() {
            var TransactionSerialNumber = 0L
            var AmountCharged = 0L
            var AmountPaid = 0L
            var TariffCode = ""
            var PenaltyCode = ""
        }

        class ModemStatus : ElgEntry() {
            var PowerMode = PowerModeEnum.OFF
            //0~99
            var SignalCSQ = 0
            //-128~127
            //VAR_INT64
            var SignaldBm = 0
        }

        class TcpIpConnection : ElgEntry() {
            var User = ""
            var Duration = 0L
            var TxBytes = 0L
            var RxBytes = 0L
        }

        class AnprOfflineDbRecordPurge : ElgEntry() {
            var RecordType = PurgedRecordTypeEnum.UNKNOWN
            var Reason = PurgedRecordReasonEnum.UNKNOWN
            var FirstTransactionSerialNo = 0L
            var LastTransactionSerialNo = 0L
        }

        class BarCode : ElgEntry() {
            var TransactionSerialNumber = 0L
            var BarcodeID = ""
        }

        class Voucher : ElgEntry() {
            var TransactionSerialNumber = 0L
            var VoucherType = VoucherSystemTypesEnum.UNKNOWN
            var VoucherNumber = ""
            var AuthorisationCode = ""
            var Status = VoucherProcessStatusEnum.FAILED
            var AmountPaid = 0L
            var IsRefund = false
        }

        class OfflineFileTransferEnd : ElgEntry() {
            var Result = OfflineFileTransferResultEnum.SUCCESS
        }

        class UiStateResult : ElgEntry() {
            var State = UiTxnStateEnum.STARTED
            var TransactionSerialNumber = 0L
            var StartTime = 0L
            var EndTime = 0L
            var Language = ""
            var RegistrationNumber = ""
            var StateHistory = ""
        }

        class X56PrintResult : ElgEntry() {
            var TransactionSerialNumber = 0L
            var PrintCmdSeqNumber = 0L
            var PrintResult = 0
            var PaperControlError = 0
            var PaperControlStatus = 0
            var PrinterStatus = 0L
        }

        class CutFailure : ElgEntry() {
            var TotalTicketsPrinted = 0L
            var TotalRetries = 0L
            var RetriesForLastTicket = 0L
        }

        class EVENT_LOG {
            val Startup = Startup()
            val ExceptionPostmortem = ExceptionPostmortem()
            val ExceptionStackDump = ExceptionStackDump()
            val StatusFlagChange = StatusFlagChange()
            val Transaction = Transaction()
            val TransportTransaction = TransportTransaction()
            val CardNonPayment = CardNonPayment()
            val CardDebit = CardDebit()
            val CardCredit = CardCredit()
            val CardRefund = CardRefund()
            val CoinDebit = CoinDebit()
            val NoteDebit = NoteDebit()
            val TokenDebit = TokenDebit()
            val CoinUnrefunded = CoinUnrefunded()
            val NoteUnrefunded = NoteUnrefunded()
            val CardUnrefunded = CardUnrefunded()
            val KeyPresented = KeyPresented()
            val TicketStock = TicketStock()
            val CardCollection = CardCollection()
            val CashBoxRemoved = CashBoxRemoved()
            val CardAuditPeriodEnd = CardAuditPeriodEnd()
            val TransactionAuditPeriodEnd = TransactionAuditPeriodEnd()
            val SpaceSystemAuditPeriodEnd = SpaceSystemAuditPeriodEnd()
            val TmsCall = TmsCall()
            val RechargeLimitChange = RechargeLimitChange()
            val TestToken = TestToken()
            val Lock = Lock()
            val PsuStatistics = PsuStatistics()
            val PsuStatus = PsuStatus()
            val APP = APP()
            val CFG = CFG()
            val TRF = TRF()
            val DKL = DKL()
            val HTL = HTL()
            val CLT = CLT()
            val PIC = PIC()
            val BL3 = BL3()
            val LUL = LUL()
            val BackOfficeCmd = BackOfficeCmd()
            val BackOfficeResp = BackOfficeResp()
            val CallReason = CallReason()
            val PenaltyTransaction = PenaltyTransaction()
            val ModemStatus = ModemStatus()
            val TcpIpConnection = TcpIpConnection()
            val AnprOfflineDbRecordPurge = AnprOfflineDbRecordPurge()
            val BarCode = BarCode()
            val Voucher = Voucher()
            val OfflineFileTransferStart = OfflineFileTransferStart()
            val OfflineFileTransferEnd = OfflineFileTransferEnd()
            val UiStateResult = UiStateResult()
            val X56PrintResult = X56PrintResult()
            val CutFailure = CutFailure()
            val VesCatSelect = VESCatSelect()
        }

    }

    private val eventItems = Vector<ElgEntry>()

    fun new(origin: String, machineUniqueID: Long) {
        try {
            synchronized(ELG::class.java) {
                eventItems.clear()
                MLog.d("sendAuditElg", "clear eventItems")
            }
        } catch (e: Exception) {
            MLog.e("sendAuditElg", "clear eventItems: $e")
        }
        create(FileType.ELG, origin, machineUniqueID)
        createTable()
    }

    fun addEventItem(log: ElgEntry = ElgEntry(), calSize: Boolean = true): Int {

        MLog.d("ELGData", "addEventItem: log: $log, calSize: $calSize")
        val size = insert(log, log::class.java.simpleName)
        if (size > 0){
            writeDataSync()
        }

        try {
            synchronized(ELG::class.java) {
                eventItems.add(log)
            }
//            KLog.d("sendAuditElg", "add: ${log.Time}")
        } catch (e: Exception) {
            MLog.e("sendAuditElg", "eventItems.add: $e")
        }

        buildSchema()

        if (calSize) {
            calHeaderSize()
            calSchemaSize()
            val bits = ArrayList<Byte>()
            if (!writeDataBase(false, bits, log, log.javaClass.simpleName)) {
                return 0
            }
            when (log) {
                is AnprOfflineDbRecordPurge -> writeData(bits, log)
                is TcpIpConnection -> writeData(bits, log)
                is ModemStatus -> writeData(bits, log)
                is CutFailure -> writeData(bits, log)
                is PenaltyTransaction -> writeData(bits, log)
                is CallReason -> writeData(bits, log)
                is BackOfficeResp -> writeData(bits, log)
                is BackOfficeCmd -> writeData(bits, log)
                is APP, is CFG, is TRF, is DKL, is HTL, is CLT, is PIC, is BL3, is LUL -> {
                    log as EVENT_LOG_MXD_SINGLE_FILE
                    writeData(bits, log)
                }
                is PsuStatistics -> writeData(bits, log)
                is X56PrintResult -> writeData(bits, log)
                is Lock -> writeData(bits, log)
                is TestToken -> writeData(bits, log)
                is RechargeLimitChange -> writeData(bits, log)
                is TmsCall -> writeData(bits, log)
                is SpaceSystemAuditPeriodEnd -> writeData(bits, log)
                is TransactionAuditPeriodEnd -> writeData(bits, log)
                is CardAuditPeriodEnd -> writeData(bits, log)
                is CashBoxRemoved -> writeData(bits, log)
                is CardCollection -> writeData(bits, log)
                is TicketStock -> writeData(bits, log)
                is KeyPresented -> writeData(bits, log)
                is TokenDebit -> writeData(bits, log)
                is EVENT_LOG_AUDIT_CASH_TRANS -> writeData(bits, log)
                is CardCredit, is CardRefund -> {
                    log as EVENT_LOG_AUDIT_CARD_CREDIT_REFUND
                    writeData(bits, log)
                }
                is CardDebit, is CardUnrefunded -> {
                    log as EVENT_LOG_AUDIT_CARD_DEBIT
                    writeData(bits, log)
                }
                is CardNonPayment -> writeData(bits, log)
                is Transaction -> writeData(bits, log)
                is VESCatSelect -> writeData(bits, log)
                is Voucher -> writeData(bits, log)
                is TransportTransaction -> writeData(bits, log)
                is StatusFlagChange -> writeData(bits, log)
                is ExceptionPostmortem -> writeData(bits, log)
                is Startup -> writeData(bits, log)
                is ExceptionStackDump -> writeData(bits, log)
                is UiStateResult -> writeData(bits, log)
            }
            calDataSize(bits.size)
            return calFileSize()
        }
        return 0
    }

    private fun buildSchema() {
        if (eventItems.isEmpty() || schema.isNotEmpty()) {
            return
        }

        //Rec 0:EVENT_LOG_OFFLINE_FILE_TRANSFER_START
        var record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        schema.add(record)

        //Rec 1:EVENT_LOG_STARTUP
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "StartupReason"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "AccumulatorVoltage"))
        schema.add(record)

        //Rec 2:EVENT_LOG_EXCEPTION_POSTMORTEM
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "CrashReason"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Registers", true))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Psr"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Task"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TaskStackStart"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TaskStackEnd"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TaskName"))
        schema.add(record)

        //Rec 3:EVENT_LOG_STATUS_FLAG_CHANGE
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Set"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Dev"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Flag"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Level"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "DevDesc"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FlagDesc"))
        schema.add(record)

        //Rec 4:EVENT_LOG_AUDIT_TRANSACTION
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "TransactionType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountCharged"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TariffCode"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EndTime"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "RegistrationNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SpaceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "ZoneId"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "VrmSelected"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "ConcessionEntered"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ConcessionCode"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "LoyaltyID"))
        schema.add(record)

        //Rec 5:EVENT_LOG_AUDIT_TRANSPORT_TRANS
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountCharged"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EndTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "NumberOfPassengers"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TariffCode"))
        schema.add(record)

        //Rec 6:EVENT_LOG_AUDIT_CARD_NON_PAYMENT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "CardType"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "CardNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Status"))
        schema.add(record)

        //Rec 7:EVENT_LOG_AUDIT_CARD_DEBIT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "CardType"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "CardNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Iso4217Code"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "AuthorisationCode"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Status"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Balance"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TerminalId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "LoyaltyID"))
        schema.add(record)

        //Rec 8:EVENT_LOG_AUDIT_CARD_CREDIT_REFUND
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "CardType"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "CardNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Iso4217Code"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "AuthorisationCode"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Status"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountCredited"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Balance"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TerminalId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "LoyaltyID"))
        schema.add(record)

        //Rec 9:EVENT_LOG_AUDIT_CASH_TRANS
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        schema.add(record)

        //Rec 10:AUDIT_TOKEN_TRANS_INFO
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TokenChannelId"))
        schema.add(record)

        //Rec 11:EVENT_LOG_AUDIT_TOKEN_TRANS
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(10, "TokenInfo", true))
        schema.add(record)

        //Rec 12:EVENT_LOG_AUDIT_KEY_PRESENTED
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "KeyNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "KeyType"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Accepted"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "PresentationTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SerialNo"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Name"))
        schema.add(record)

        //Rec 13:EVENT_LOG_AUDIT_TICKET_STOCK_EVENT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Printer"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TimeChanged"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "OldRollLength"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TicketsUsed"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "NewRollLength"))
        schema.add(record)

        //Rec 14:EVENT_LOG_AUDIT_CARD_COLLECTION
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "TriggerType"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "CardType"))
        schema.add(record)

        //Rec 15:AUDIT_CASH_PERIOD_ITEM
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "Iso4217Code"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Denomination"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Count"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "UnrefundedCount"))
        schema.add(record)

        //Rec 16:AUDIT_CASH_PERIOD_GRAND_TOTAL
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "Iso4217Code"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "DecimalPlaces"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "GrandTotalAtLastCashBoxPull"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "UnrefundedAtLastCashBoxPull"))
        schema.add(record)

        //Rec 17:AUDIT_CASH_PERIOD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CashboxPullNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EndTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Transactions"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Volume"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Value"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "nItems"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "nCurrencyGrandTotals"))
        record.elements.add(Element(15, "Item", true))
        record.elements.add(Element(16, "CurrencyGrandTotal", true))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "UnRefundedTransactions"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CumTotalTransactions"))
        schema.add(record)

        //Rec 18:EVENT_LOG_AUDIT_CASH_BOX_REMOVED
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "BoxType"))
        record.elements.add(Element(17, "Data"))
        schema.add(record)

        //Rec 19:AUDIT_CARD_SYSTEM
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "CardType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "DebitTransactions"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "DebitAmount"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CreditTransactions"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CreditAmount"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "RefundedAmount"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "UnRefundedAmount"))
        schema.add(record)

        //Rec 20:AUDIT_CARD_PERIOD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AuditNo"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EndTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CumDebitTransactions"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CumDebitAmount"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CumCreditTransactions"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CumCreditAmount"))
        record.elements.add(Element(19, "CardSystem", true))
        schema.add(record)

        //Rec 21:EVENT_LOG_AUDIT_CARD_PERIOD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "TriggerType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TriggerSequenceNumber"))
        record.elements.add(Element(20, "Data"))
        schema.add(record)

        //Rec 22:AUDIT_TRANSACTION_TIMEBAND_AMOUNTS2
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "A"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "B"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "C"))
        schema.add(record)

        //Rec 23:AUDIT_TRANSACTION_TIMEBAND_AMOUNTS
        record = Element()
        record.elements.add(Element(22, "NoFreeTimeInterval"))
        record.elements.add(Element(22, "FreeTimeInterval"))
        record.elements.add(Element(22, "TicketsValue"))
        schema.add(record)

        //Rec 24:AUDIT_TRANSACTION_CATEGORY_AMOUNTS
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalAmount"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalTickets"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalFreeTickets"))
        schema.add(record)

        //Rec 25:AUDIT_TRANSACTION_PERIOD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AuditNo"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EndTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "DebitTransactions"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CreditTransactions"))
        record.elements.add(Element(23, "TimeBands", true))
        record.elements.add(Element(24, "Categories", true))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalCreditAmount"))
        schema.add(record)

        //Rec 26:EVENT_LOG_AUDIT_TRANSACTION_PERIOD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "TriggerType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TriggerSequenceNumber"))
        record.elements.add(Element(25, "Data"))
        schema.add(record)

        //Rec 27:AUDIT_SPACE_SYSTEM_ZONE
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "ZoneId"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalTransaction"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalAmountPaid"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalAmountCharged"))
        schema.add(record)

        //Rec 28:AUDIT_SPACE_SYSTEM_PERIOD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AuditNo"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EndTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "nZones"))
        record.elements.add(Element(27, "Zones"))
        schema.add(record)

        //Rec 29:EVENT_LOG_AUDIT_SPACE_SYSTEM_PERIOD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "TriggerType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TriggerSequenceNumber"))
        record.elements.add(Element(28, "Data"))
        schema.add(record)

        //Rec 30:EVENT_LOG_AUDIT_TMS_CALL
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "CardReaderType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Duration"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Status"))
        schema.add(record)

        //Rec 31:EVENT_LOG_RECHARGE_LIMIT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Expiry"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Quantity"))
        schema.add(record)

        //Rec 32:EVENT_LOG_TEST_TOKEN
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Action"))
        schema.add(record)

        //Rec 33:EVENT_LOG_LOCK
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "LockType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "KeyPresentationTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "KeyNumber"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Succeeded"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "LockStatus"))
        schema.add(record)

        //Rec 34:PSU_STATISTICS_AV_MIN_MAX
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "Average"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "Min"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "Max"))
        schema.add(record)

        //Rec 35:EVENT_LOG_PSU_ACCUMULATOR
        record = Element()
        record.elements.add(Element(34, "CurrentAcc"))
        record.elements.add(Element(34, "VoltageAcc"))
        record.elements.add(Element(34, "Temperature"))
        schema.add(record)

        //Rec 36:EVENT_LOG_PSU_STATISTICS_EXT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SampleCount"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "MainsOnSampleCount"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SolarOnSampleCount"))
//        record.elements.add(Element(34, "CurrentAcc"))
//        record.elements.add(Element(34, "VoltageAcc"))
//        record.elements.add(Element(34, "Temperature"))
        record.elements.add(Element(35, "Accumulator1"))
        record.elements.add(Element(35, "Accumulator2"))
        schema.add(record)

        //Rec 37:TEMP_PSU_ACCUMULATOR
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "VoltageAcc"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "CurrentAcc"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "Temperature"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "AccState"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "ChargeState"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "LastReadVoltageAcc"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "NewAccState"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "nDischargeReadings"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AccumulatorNo"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Missing"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "VoltageAccMV"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "CurrentAccMA"))
        schema.add(record)

        //Rec 38:TEMP_PSU_EXT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "PsuState"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SupplyVoltage"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SupplyCurrent"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FwVersion"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "BoardIssue"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SystemFlags"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SystemStatus"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "ALT_Status_0"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Solar"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "Mains"))
        record.elements.add(Element(37, "Accumulator1"))
        record.elements.add(Element(37, "Accumulator2"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SupplyVoltageMV"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SupplyCurrentMA"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "ChargerState"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "ChargerVoltageMV"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SolarVoltageMV"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SolarCurrentMA"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SolarOCVoltageMV"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SleepCurrentMA"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SolarSCCurrentMA"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "BoardTemperature"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "BatteryMode"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "PrinterOn"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "ExtraTempSensors"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "DataValid"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "A1"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "B1"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "C1"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "D1"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "E1"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "F1"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "A2"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "B2"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "C2"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "D2"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "E2"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "F2"))
        schema.add(record)

        //Rec 39:EVENT_LOG_PSU_STATUS
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(38, "Status"))
        schema.add(record)

        //Rec 40:Entry
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

        //Rec 41:EVENT_LOG_MXD_SINGLE_FILE
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(40, "File"))
        schema.add(record)

        //Rec 42:BACK_OFFICE_CMD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SerialNo"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Command"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "NumberPar1"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "StringPar1"))
        schema.add(record)

        //Rec 43:EVENT_LOG_BACK_OFFICE_CMD
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(42, "Data"))
        schema.add(record)

        //Rec 44:BACK_OFFICE_RESP
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SerialNo"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Response"))
        schema.add(record)

        //Rec 45:EVENT_LOG_BACK_OFFICE_RESP
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(44, "Data"))
        schema.add(record)

        //Rec 46:EVENT_LOG_CALL_REASON
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SessionSerialNo"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "ApplicationStart"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "StatusFlagChange"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "ScheduledCall"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "BackOfficeCall"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "RetryAfterBusy"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "RetryAfterFailure"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "TestCall"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "ForcedCall"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "ImmediateJob"))
        schema.add(record)

        //Rec 47:EVENT_LOG_JENIMEX_PENALTY_PAYMENT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountCharged"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TariffCode"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "PenaltyCode"))
        schema.add(record)

        //Rec 48:EVENT_LOG_MODEM_STATUS
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "PowerMode"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SignalCSQ"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "SignaldBm"))
        schema.add(record)

        //Rec 49:EVENT_LOG_TCPIP_CONNECTION
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "User"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Duration"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TxBytes"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "RxBytes"))
        schema.add(record)

        //Rec 50:EVENT_LOG_ANPR_OFFL_DB_RECORD_PURGE
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "RecordType"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Reason"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "FirstTransactionSerialNo"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "LastTransactionSerialNo"))
        schema.add(record)

        //Rec 51:EVENT_LOG_BARCODE
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "BarcodeID"))
        schema.add(record)

        //Rec 52:EVENT_LOG_AUDIT_VOUCHER
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "VoucherType"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "VoucherNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "AuthorisationCode"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Status"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(DataType.MXDDT_BOOL, "IsRefund"))
        schema.add(record)

        //Rec 53:EVENT_LOG_OFFLINE_FILE_TRANSFER_END
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Result"))
        schema.add(record)

        //Rec 54:EVENT_LOG_UI_STATE_RESULT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "State"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "StartTime"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "EndTime"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Language"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "RegistrationNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "StateHistory"))
        schema.add(record)

        //Rec 55:EVENT_LOG_X56_PRINT_RESULT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "PrintCmdSeqNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "PrintResult"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "PaperControlError"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "PaperControlStatus"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "PrinterStatus"))
        schema.add(record)

        //Rec 56:CUT_FAILURE
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalTicketsPrinted"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TotalRetries"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "RetriesForLastTicket"))
        schema.add(record)

        //Rec 57:VES_RESPONSE
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "HTTPStatus"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FuelType"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "Co2"))
        record.elements.add(Element(DataType.MXDDT_VAR_INT64, "EngineCC"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ErrorDesc"))
        schema.add(record)

        //Rec 58:VES_RESULT
        record = Element()
        record.elements.add(Element(57, "VesResponse"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SelectionReason"))
        schema.add(record)

        //Rec 59:VES_CAT_SELECT
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "RegistrationNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "SelectedTariffCategoryRule"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(58, "VesResult"))
        schema.add(record)

        //Rec 60: ExceptionStackDump
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ExceptionType"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "Message"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "StackTrace"))
        schema.add(record)

        //Rec 61: Other Transaction Card Details
        record = Element()
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "CardNumber"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "CardType"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TransactionReference"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Iso4217Code"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "AuthorisationCode"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "TerminalId"))
        schema.add(record)

        //Rec 62: Other Transaction Cash Details
        record = Element()
        record.elements.add(Element(DataType.MXDDT_ENUM, "CashType"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "Iso4217Code"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountPaid"))
        schema.add(record)

        //Rec 63: Other Transaction Details
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionSerialNumber"))
        record.elements.add(Element(DataType.MXDDT_ENUM, "TransactionType"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "AmountCharged"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "TransactionTime"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "ForeignId"))
        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "RegistrationNumber"))
        record.elements.add(Element(61, "CardDetails", isArray = true))
        record.elements.add(Element(62, "CashDetails", isArray = true))
        schema.add(record)

        //Rec 64:EVENT_LOG
        record = Element()
        record.isChoice = true
        record.elements.add(Element(1, Startup::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(2, ExceptionPostmortem::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(3, StatusFlagChange::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(4, Transaction::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(5, TransportTransaction::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(6, CardNonPayment::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(7, CardDebit::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(8, CardCredit::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(8, CardRefund::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(9, CoinDebit::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(9, NoteDebit::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(11, TokenDebit::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(9, CoinUnrefunded::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(9, NoteUnrefunded::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(12, KeyPresented::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(13, TicketStock::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(14, CardCollection::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(18, CashBoxRemoved::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(21, CardAuditPeriodEnd::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(26, TransactionAuditPeriodEnd::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(29, SpaceSystemAuditPeriodEnd::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(30, TmsCall::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(31, RechargeLimitChange::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(32, TestToken::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(33, Lock::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(36, PsuStatistics::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(39, PsuStatus::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, APP::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, CFG::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, TRF::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, DKL::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, HTL::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, CLT::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, PIC::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, BL3::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(41, LUL::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(43, BackOfficeCmd::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(45, BackOfficeResp::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(46, CallReason::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(47, PenaltyTransaction::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(48, ModemStatus::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(49, TcpIpConnection::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(50, AnprOfflineDbRecordPurge::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(51, BarCode::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(52, Voucher::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(0, OfflineFileTransferStart::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(53, OfflineFileTransferEnd::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(54, UiStateResult::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(55, X56PrintResult::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(56, CutFailure::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(59, VESCatSelect::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(7, CardUnrefunded::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(60, ExceptionStackDump::class.simpleName, isArray = false, isChoice = true))
        record.elements.add(Element(63, OtherTransaction::class.simpleName, isArray = false, isChoice = true))
        schema.add(record)
    }

    private fun writeDataBase(newSequenceNumber: Boolean, bits: ArrayList<Byte>, log: ElgEntry, fieldName: String?): Boolean {
        val index = findIndex(fieldName)
        if (index < 0) {
            return false
        }
        bits.addAll(write7BitUint(index))
        bits.addAll(write7BitUint(log.Time))
        if (newSequenceNumber) {
            log.newSequenceNumber()
        }
        bits.addAll(write7BitUint(log.SequenceNumber))
        return true
    }

    private fun writeData(bits: ArrayList<Byte>, log: AnprOfflineDbRecordPurge) {
        bits.addAll(writeEnum(log.RecordType))
        bits.addAll(writeEnum(log.Reason))
        bits.addAll(write7BitUint(log.FirstTransactionSerialNo))
        bits.addAll(write7BitUint(log.LastTransactionSerialNo))
    }
    private fun writeData(bits: ArrayList<Byte>, log: TcpIpConnection) {
        bits.addAll(writeString(log.User))
        bits.addAll(write7BitUint(log.Duration))
        bits.addAll(write7BitUint(log.TxBytes))
        bits.addAll(write7BitUint(log.RxBytes))
    }
    private fun writeData(bits: ArrayList<Byte>, log: ModemStatus) {
        bits.addAll(writeEnum(log.PowerMode))
        bits.addAll(write7BitUint(log.SignalCSQ))
        bits.addAll(write7BitInt(log.SignaldBm))
    }
    private fun writeData(bits: ArrayList<Byte>, log: CutFailure) {
        bits.addAll(write7BitUint(log.TotalTicketsPrinted))
        bits.addAll(write7BitUint(log.TotalRetries))
        bits.addAll(write7BitUint(log.RetriesForLastTicket))
    }
    private fun writeData(bits: ArrayList<Byte>, log: PenaltyTransaction) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(write7BitUint(log.AmountCharged))
        bits.addAll(write7BitUint(log.AmountPaid))
        bits.addAll(writeString(log.TariffCode))
        bits.addAll(writeString(log.PenaltyCode))
    }
    private fun writeData(bits: ArrayList<Byte>, log: CallReason) {
        bits.addAll(write7BitUint(log.SessionSerialNo))
        bits.addAll(writeBoolean(log.ApplicationStart))
        bits.addAll(writeBoolean(log.StatusFlagChange))
        bits.addAll(writeBoolean(log.ScheduledCall))
        bits.addAll(writeBoolean(log.BackOfficeCall))
        bits.addAll(writeBoolean(log.RetryAfterBusy))
        bits.addAll(writeBoolean(log.RetryAfterFailure))
        bits.addAll(writeBoolean(log.TestCall))
        bits.addAll(writeBoolean(log.ForcedCall))
        bits.addAll(writeBoolean(log.ImmediateJob))
    }
    private fun writeData(bits: ArrayList<Byte>, log: BackOfficeResp) {
        bits.addAll(write7BitUint(log.Data.SerialNo))
        bits.addAll(writeEnum(log.Data.Response))
    }
    private fun writeData(bits: ArrayList<Byte>, log: BackOfficeCmd) {
        bits.addAll(write7BitUint(log.Data.SerialNo))
        bits.addAll(writeEnum(log.Data.Command))
        bits.addAll(write7BitUint(log.Data.NumberPar1))
        bits.addAll(writeString(log.Data.StringPar1))
    }
    private fun writeData(bits: ArrayList<Byte>, log: EVENT_LOG_MXD_SINGLE_FILE) {
        bits.addAll(write7BitUint(log.File.FileSize))
        bits.addAll(write7BitUint(log.File.FileCrc))
        bits.addAll(writeString(log.File.FileName))
        bits.addAll(writeString(log.File.Customer))
        bits.addAll(write7BitUint(log.File.CreationTime))
        bits.addAll(writeEnum(log.File.ContentType))
        bits.addAll(writeString(log.File.Version))
        bits.addAll(write7BitUint(log.File.EncryptionType))
        bits.addAll(write7BitUint(log.File.ValidFromTime))
        bits.addAll(write7BitUint(log.File.CompatibilityLevel))
        bits.addAll(write7BitInt(log.File.CreationTz))
        bits.addAll(write7BitInt(log.File.ValidFromTz))
    }
    private fun writeData(bits: ArrayList<Byte>, log: PsuStatistics) {
        bits.addAll(write7BitUint(log.SampleCount))
        bits.addAll(write7BitUint(log.MainsOnSampleCount))
        bits.addAll(write7BitUint(log.SolarOnSampleCount))
//        bits.add(write7BitInt(log.CurrentAcc.Average))
//        bits.add(write7BitInt(log.CurrentAcc.Min))
//        bits.add(write7BitInt(log.CurrentAcc.Max))
//        bits.add(write7BitInt(log.VoltageAcc.Average))
//        bits.add(write7BitInt(log.VoltageAcc.Min))
//        bits.add(write7BitInt(log.VoltageAcc.Max))
//        bits.add(write7BitInt(log.Temperature.Average))
//        bits.add(write7BitInt(log.Temperature.Min))
//        bits.add(write7BitInt(log.Temperature.Max))
        bits.addAll(write7BitInt(log.Accumulator1.CurrentAcc.Average))
        bits.addAll(write7BitInt(log.Accumulator1.CurrentAcc.Min))
        bits.addAll(write7BitInt(log.Accumulator1.CurrentAcc.Max))
        bits.addAll(write7BitInt(log.Accumulator1.VoltageAcc.Average))
        bits.addAll(write7BitInt(log.Accumulator1.VoltageAcc.Min))
        bits.addAll(write7BitInt(log.Accumulator1.VoltageAcc.Max))
        bits.addAll(write7BitInt(log.Accumulator1.Temperature.Average))
        bits.addAll(write7BitInt(log.Accumulator1.Temperature.Min))
        bits.addAll(write7BitInt(log.Accumulator1.Temperature.Max))
        bits.addAll(write7BitInt(log.Accumulator2.CurrentAcc.Average))
        bits.addAll(write7BitInt(log.Accumulator2.CurrentAcc.Min))
        bits.addAll(write7BitInt(log.Accumulator2.CurrentAcc.Max))
        bits.addAll(write7BitInt(log.Accumulator2.VoltageAcc.Average))
        bits.addAll(write7BitInt(log.Accumulator2.VoltageAcc.Min))
        bits.addAll(write7BitInt(log.Accumulator2.VoltageAcc.Max))
        bits.addAll(write7BitInt(log.Accumulator2.Temperature.Average))
        bits.addAll(write7BitInt(log.Accumulator2.Temperature.Min))
        bits.addAll(write7BitInt(log.Accumulator2.Temperature.Max))
    }
    private fun writeData(bits: ArrayList<Byte>, log: X56PrintResult) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(write7BitUint(log.PrintCmdSeqNumber))
        bits.addAll(write7BitInt(log.PrintResult))
        bits.addAll(write7BitUint(log.PaperControlError))
        bits.addAll(write7BitUint(log.PaperControlStatus))
        bits.addAll(write7BitUint(log.PrinterStatus))
    }
    private fun writeData(bits: ArrayList<Byte>, log: Lock) {
        bits.addAll(writeEnum(log.LockType))
        bits.addAll(write7BitUint(log.KeyPresentationTime))
        bits.addAll(write7BitInt(log.KeyNumber))
        bits.addAll(writeBoolean(log.Succeeded))
        bits.addAll(writeEnum(log.LockStatus))
    }
    private fun writeData(bits: ArrayList<Byte>, log: TestToken) {
        bits.addAll(writeEnum(log.Action))
    }
    private fun writeData(bits: ArrayList<Byte>, log: RechargeLimitChange) {
        bits.addAll(write7BitUint(log.Expiry))
        bits.addAll(write7BitUint(log.Quantity))
    }
    private fun writeData(bits: ArrayList<Byte>, log: TmsCall) {
        bits.addAll(writeString(log.CardReaderType))
        bits.addAll(write7BitUint(log.StartTime))
        bits.addAll(write7BitUint(log.Duration))
        bits.addAll(writeEnum(log.Status))
    }
    private fun writeData(bits: ArrayList<Byte>, log: SpaceSystemAuditPeriodEnd) {
        bits.addAll(writeEnum(log.TriggerType))
        bits.addAll(write7BitUint(log.TriggerSequenceNumber))
        bits.addAll(write7BitUint(log.Data.AuditNo))
        bits.addAll(write7BitUint(log.Data.StartTime))
        bits.addAll(write7BitUint(log.Data.EndTime))
        bits.addAll(write7BitUint(log.Data.nZones))
        bits.addAll(write7BitUint(log.Data.Zones.size))
        for (zone in log.Data.Zones) {
            bits.addAll(write7BitUint(zone.ZoneId))
            bits.addAll(write7BitUint(zone.TotalTransaction))
            bits.addAll(write7BitUint(zone.TotalAmountPaid))
            bits.addAll(write7BitUint(zone.TotalAmountCharged))
        }
    }
    private fun writeData(bits: ArrayList<Byte>, log: TransactionAuditPeriodEnd) {
        bits.addAll(writeEnum(log.TriggerType))
        bits.addAll(write7BitUint(log.TriggerSequenceNumber))
        bits.addAll(write7BitUint(log.Data.AuditNo))
        bits.addAll(write7BitUint(log.Data.StartTime))
        bits.addAll(write7BitUint(log.Data.EndTime))
        bits.addAll(write7BitUint(log.Data.DebitTransactions))
        bits.addAll(write7BitUint(log.Data.CreditTransactions))
        bits.addAll(write7BitUint(log.Data.TimeBands.size))//增加后后台解析成后
        for (timeBand in log.Data.TimeBands) {
            bits.addAll(write7BitUint(timeBand.NoFreeTimeInterval.A))
            bits.addAll(write7BitUint(timeBand.NoFreeTimeInterval.B))
            bits.addAll(write7BitUint(timeBand.NoFreeTimeInterval.C))
            bits.addAll(write7BitUint(timeBand.FreeTimeInterval.A))
            bits.addAll(write7BitUint(timeBand.FreeTimeInterval.B))
            bits.addAll(write7BitUint(timeBand.FreeTimeInterval.C))
            bits.addAll(write7BitUint(timeBand.TicketsValue.A))
            bits.addAll(write7BitUint(timeBand.TicketsValue.B))
            bits.addAll(write7BitUint(timeBand.TicketsValue.C))
        }
        bits.addAll(write7BitUint(log.Data.Categories.size))//增加后后台解析成后
        for (category in log.Data.Categories) {
            bits.addAll(write7BitUint(category.TotalAmount))
            bits.addAll(write7BitUint(category.TotalTickets))
            bits.addAll(write7BitUint(category.TotalFreeTickets))
        }
        bits.addAll(write7BitUint(log.Data.TotalCreditAmount))
    }
    private fun writeData(bits: ArrayList<Byte>, log: CardAuditPeriodEnd) {
        bits.addAll(writeEnum(log.TriggerType))
        bits.addAll(write7BitUint(log.TriggerSequenceNumber))
        bits.addAll(write7BitUint(log.Data.AuditNo))
        bits.addAll(write7BitUint(log.Data.StartTime))
        bits.addAll(write7BitUint(log.Data.EndTime))
        bits.addAll(write7BitUint(log.Data.CumDebitTransactions))
        bits.addAll(write7BitUint(log.Data.CumDebitAmount))
        bits.addAll(write7BitUint(log.Data.CumCreditTransactions))
        bits.addAll(write7BitUint(log.Data.CumCreditAmount))
        bits.addAll(write7BitUint(log.Data.CardSystem.size))//增加后后台解析成后
        for (cardSystem in log.Data.CardSystem) {
            bits.addAll(writeEnum(cardSystem.CardType))
            bits.addAll(write7BitUint(cardSystem.DebitTransactions))
            bits.addAll(write7BitUint(cardSystem.DebitAmount))
            bits.addAll(write7BitUint(cardSystem.CreditTransactions))
            bits.addAll(write7BitUint(cardSystem.CreditAmount))
            bits.addAll(write7BitUint(cardSystem.RefundedAmount))
            bits.addAll(write7BitUint(cardSystem.UnRefundedAmount))
        }
    }
    private fun writeData(bits: ArrayList<Byte>, log: CashBoxRemoved) {
        bits.addAll(writeEnum(log.BoxType))
        bits.addAll(write7BitUint(log.Data.CashboxPullNumber))
        bits.addAll(write7BitUint(log.Data.StartTime))
        bits.addAll(write7BitUint(log.Data.EndTime))
        bits.addAll(write7BitUint(log.Data.Transactions))
        bits.addAll(write7BitUint(log.Data.Volume))
        bits.addAll(write7BitUint(log.Data.Value))
        bits.addAll(write7BitUint(log.Data.nItems))
        bits.addAll(write7BitUint(log.Data.nCurrencyGrandTotals))
        bits.addAll(write7BitUint(log.Data.Item.size))//增加后后台解析成后
        for (item in log.Data.Item) {
            bits.addAll(writeEnum(item.Iso4217Code))
            bits.addAll(write7BitUint(item.Denomination))
            bits.addAll(write7BitUint(item.Count))
            bits.addAll(write7BitUint(item.UnrefundedCount))
        }
        bits.addAll(write7BitUint(log.Data.CurrencyGrandTotal.size))//增加后后台解析成后
        for (currencyGrandTotal in log.Data.CurrencyGrandTotal) {
            bits.addAll(writeEnum(currencyGrandTotal.Iso4217Code))
            bits.addAll(write7BitUint(currencyGrandTotal.DecimalPlaces))
            bits.addAll(write7BitUint(currencyGrandTotal.GrandTotalAtLastCashBoxPull))
            bits.addAll(write7BitUint(currencyGrandTotal.UnrefundedAtLastCashBoxPull))
        }
        bits.addAll(write7BitUint(log.Data.UnRefundedTransactions))
        bits.addAll(write7BitUint(log.Data.CumTotalTransactions))
    }
    private fun writeData(bits: ArrayList<Byte>, log: CardCollection) {
        bits.addAll(writeEnum(log.TriggerType))
        bits.addAll(writeEnum(log.CardType))
    }
    private fun writeData(bits: ArrayList<Byte>, log: TicketStock) {
        bits.addAll(writeEnum(log.Printer))
        bits.addAll(write7BitUint(log.TimeChanged))
        bits.addAll(write7BitUint(log.OldRollLength))
        bits.addAll(write7BitUint(log.TicketsUsed))
        bits.addAll(write7BitUint(log.NewRollLength))
    }
    private fun writeData(bits: ArrayList<Byte>, log: KeyPresented) {
        bits.addAll(write7BitUint(log.KeyNumber))
        bits.addAll(writeEnum(log.KeyType))
        bits.addAll(writeBoolean(log.Accepted))
        bits.addAll(write7BitUint(log.PresentationTime))
        bits.addAll(write7BitUint(log.SerialNo))
        bits.addAll(writeString(log.Name))
    }
    private fun writeData(bits: ArrayList<Byte>, log: TokenDebit) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(write7BitUint(log.AmountPaid))
        bits.addAll(write7BitUint(log.TokenInfo.size))
        for (tokenInfo in log.TokenInfo) {
            bits.addAll(write7BitUint(tokenInfo.AmountPaid))
            bits.addAll(writeString(tokenInfo.TokenChannelId))
        }
    }
    private fun writeData(bits: ArrayList<Byte>, log: EVENT_LOG_AUDIT_CASH_TRANS) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(write7BitUint(log.AmountPaid))
    }
    private fun writeData(bits: ArrayList<Byte>, log: EVENT_LOG_AUDIT_CARD_CREDIT_REFUND) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(writeEnum(log.CardType))
        bits.addAll(writeString(log.CardNumber))
        bits.addAll(writeEnum(log.Iso4217Code))
        bits.addAll(writeString(log.AuthorisationCode))
        bits.addAll(writeEnum(log.Status))
        bits.addAll(write7BitUint(log.AmountCredited))
        bits.addAll(write7BitUint(log.Balance))
        bits.addAll(writeString(log.TerminalId))
        bits.addAll(writeString(log.LoyaltyID))
    }
    private fun writeData(bits: ArrayList<Byte>, log: EVENT_LOG_AUDIT_CARD_DEBIT) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(writeEnum(log.CardType))
        bits.addAll(writeString(log.CardNumber))
        bits.addAll(writeEnum(log.Iso4217Code))
        bits.addAll(writeString(log.AuthorisationCode))
        bits.addAll(writeEnum(log.Status))
        bits.addAll(write7BitUint(log.AmountPaid))
        bits.addAll(write7BitUint(log.Balance))
        bits.addAll(writeString(log.TerminalId))
        bits.addAll(writeString(log.LoyaltyID))
    }
    private fun writeData(bits: ArrayList<Byte>, log: CardNonPayment) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(writeEnum(log.CardType))
        bits.addAll(writeString(log.CardNumber))
        bits.addAll(writeEnum(log.Status))
    }
    private fun writeData(bits: ArrayList<Byte>, log: TransportTransaction) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(write7BitUint(log.AmountCharged))
        bits.addAll(write7BitUint(log.StartTime))
        bits.addAll(write7BitUint(log.EndTime))
        bits.addAll(write7BitUint(log.NumberOfPassengers))
        bits.addAll(writeString(log.TariffCode))
    }
    private fun writeData(bits: ArrayList<Byte>, log: Transaction) {
        bits.addAll(writeEnum(log.TransactionType))
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(write7BitUint(log.AmountCharged))
        bits.addAll(write7BitUint(log.AmountPaid))
        bits.addAll(writeString(log.TariffCode))
        bits.addAll(write7BitUint(log.StartTime))
        bits.addAll(write7BitUint(log.EndTime))
        bits.addAll(writeString(log.RegistrationNumber))
        bits.addAll(write7BitUint(log.SpaceNumber))
        bits.addAll(write7BitUint(log.ZoneId))
        bits.addAll(writeEnum(log.VrmSelected))
        bits.addAll(writeEnum(log.ConcessionEntered))
        bits.addAll(writeString(log.ConcessionCode))
        bits.addAll(writeString(log.LoyaltyID))
    }

    private fun writeData(bits: ArrayList<Byte>, log: VESCatSelect) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(writeString(log.RegistrationNumber))
        bits.addAll(writeString(log.SelectedTariffCategoryRule))
        bits.addAll(write7BitUint(log.AmountPaid))
        bits.addAll(write7BitInt(log.VesResult.VesResponse.HTTPStatus))
        bits.addAll(writeString(log.VesResult.VesResponse.FuelType))
        bits.addAll(write7BitInt(log.VesResult.VesResponse.Co2))
        bits.addAll(write7BitInt(log.VesResult.VesResponse.EngineCC))
        bits.addAll(writeString(log.VesResult.VesResponse.ErrorDesc))
        bits.addAll(writeString(log.VesResult.SelectionReason))
    }

    private fun writeData(bits: ArrayList<Byte>, log: Voucher) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(writeEnum(log.VoucherType))
        bits.addAll(writeString(log.VoucherNumber))
        bits.addAll(writeString(log.AuthorisationCode))
        bits.addAll(writeEnum(log.Status))
        bits.addAll(write7BitUint(log.AmountPaid))
        bits.addAll(writeBoolean(log.IsRefund))
    }

    private fun writeData(bits: ArrayList<Byte>, log: StatusFlagChange) {
        //
        //record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Time"))
        //        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "SequenceNumber"))
        //        record.elements.add(Element(DataType.MXDDT_BOOL, "Set"))
        //        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Dev"))
        //        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Flag"))
        //        record.elements.add(Element(DataType.MXDDT_ENUM, "Level"))
        //        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "DevDesc"))
        //        record.elements.add(Element(DataType.MXDDT_UTF8_STRING, "FlagDesc"))
        bits.addAll(writeBoolean(log.Set))
        bits.addAll(write7BitUint(log.Dev))
        bits.addAll(write7BitUint(log.Flag))
        bits.addAll(writeEnum(log.Level))
        bits.addAll(writeString(log.DevDesc))
        bits.addAll(writeString(log.FlagDesc))
    }
    private fun writeData(bits: ArrayList<Byte>, log: ExceptionPostmortem) {
        bits.addAll(writeEnum(log.CrashReason))
        bits.addAll(write7BitUint(log.Registers.size))
        for (register in log.Registers) {
            bits.addAll(write7BitUint(register))
        }
        bits.addAll(write7BitUint(log.Psr))
        bits.addAll(write7BitUint(log.Task))
        bits.addAll(write7BitUint(log.TaskStackStart))
        bits.addAll(write7BitUint(log.TaskStackEnd))
        bits.addAll(writeString(log.TaskName))
    }
    private fun writeData(bits: ArrayList<Byte>, log: Startup) {
        bits.addAll(writeEnum(log.StartupReason))
        bits.addAll(write7BitUint(log.AccumulatorVoltage))
    }

    private fun writeData(bits: ArrayList<Byte>, log: ExceptionStackDump) {
        bits.addAll(writeString(log.ExceptionType))
        bits.addAll(writeString(log.Message))
        bits.addAll(writeString(log.StackTrace))
    }

    private fun writeData(bits: ArrayList<Byte>, log: UiStateResult) {
        bits.addAll(writeEnum(log.State))
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(write7BitUint(log.StartTime))
        bits.addAll(write7BitUint(log.EndTime))
        bits.addAll(writeString(log.Language))
        bits.addAll(writeString(log.RegistrationNumber))
        bits.addAll(writeString(log.StateHistory))
    }

    private fun writeData(bits: ArrayList<Byte>, log: OtherTransaction) {
        bits.addAll(write7BitUint(log.TransactionSerialNumber))
        bits.addAll(writeEnum(log.TransactionType))
        bits.addAll(write7BitUint(log.AmountCharged))
        bits.addAll(write7BitUint(log.TransactionTime))
        bits.addAll(writeString(log.ForeignId))
        bits.addAll(writeString(log.RegistrationNumber))
        bits.addAll(write7BitUint(log.CardDetails.size))
        log.CardDetails.forEach {
            bits.addAll(writeString(it.CardNumber))
            bits.addAll(writeString(it.CardType))
            bits.addAll(writeString(it.TransactionReference))
            bits.addAll(writeEnum(it.Iso4217Code))
            bits.addAll(writeString(it.AuthorisationCode))
            bits.addAll(write7BitUint(it.AmountPaid))
            bits.addAll(writeString(it.TerminalId))
        }
        bits.addAll(write7BitUint(log.CashDetails.size))
        log.CashDetails.forEach {
            bits.addAll(writeEnum(it.CashType))
            bits.addAll(writeEnum(it.Iso4217Code))
            bits.addAll(write7BitUint(it.AmountPaid))
        }
    }

    override fun writeData(bits: ArrayList<Byte>) {
        synchronized(ELG::class.java) {
            for (log in eventItems) {
                if (!writeDataBase(true, bits, log, log.javaClass.simpleName)) {
                    return
                }
                when (log) {
                    is AnprOfflineDbRecordPurge -> writeData(bits, log)
                    is TcpIpConnection -> writeData(bits, log)
                    is ModemStatus -> writeData(bits, log)
                    is CutFailure -> writeData(bits, log)
                    is PenaltyTransaction -> writeData(bits, log)
                    is CallReason -> writeData(bits, log)
                    is BackOfficeResp -> writeData(bits, log)
                    is BackOfficeCmd -> writeData(bits, log)
                    is APP, is CFG, is TRF, is DKL, is HTL, is CLT, is PIC, is BL3, is LUL -> {
                        log as EVENT_LOG_MXD_SINGLE_FILE
                        writeData(bits, log)
                    }
                    is PsuStatistics -> writeData(bits, log)
                    is X56PrintResult -> writeData(bits, log)
                    is Lock -> writeData(bits, log)
                    is TestToken -> writeData(bits, log)
                    is RechargeLimitChange -> writeData(bits, log)
                    is TmsCall -> writeData(bits, log)
                    is SpaceSystemAuditPeriodEnd -> writeData(bits, log)
                    is TransactionAuditPeriodEnd -> writeData(bits, log)
                    is CardAuditPeriodEnd -> writeData(bits, log)
                    is CashBoxRemoved -> writeData(bits, log)
                    is CardCollection -> writeData(bits, log)
                    is TicketStock -> writeData(bits, log)
                    is KeyPresented -> writeData(bits, log)
                    is TokenDebit -> writeData(bits, log)
                    is EVENT_LOG_AUDIT_CASH_TRANS -> writeData(bits, log)
                    is CardCredit, is CardRefund -> {
                        log as EVENT_LOG_AUDIT_CARD_CREDIT_REFUND
                        writeData(bits, log)
                    }
                    is CardDebit, is CardUnrefunded -> {
                        log as EVENT_LOG_AUDIT_CARD_DEBIT
                        writeData(bits, log)
                    }
                    is CardNonPayment -> writeData(bits, log)
                    is Transaction -> writeData(bits, log)
                    is TransportTransaction -> writeData(bits, log)
                    is VESCatSelect -> writeData(bits, log)
                    is Voucher -> writeData(bits, log)
                    is StatusFlagChange -> writeData(bits, log)
                    is ExceptionPostmortem -> writeData(bits, log)
                    is Startup -> writeData(bits, log)
                    is ExceptionStackDump -> writeData(bits, log)
                    is UiStateResult -> writeData(bits, log)
                    is OtherTransaction -> writeData(bits, log)
                }
            }
        }
        bits.add(0.toByte())
    }

    fun addAnprOfflineDbRecordPurge(recordType: PurgedRecordTypeEnum, reason: PurgedRecordReasonEnum, firstTransactionSerialNo: Long, lastTransactionSerialNo: Long): Int {
        val log = AnprOfflineDbRecordPurge()
        log.RecordType = recordType
        log.Reason = reason
        log.FirstTransactionSerialNo = firstTransactionSerialNo
        log.LastTransactionSerialNo = lastTransactionSerialNo
        return addEventItem(log)
    }

    fun addTcpIpConnection(user: String, duration: Long, txBytes: Long, rxBytes: Long, calSize: Boolean = true): Int {
        val log = TcpIpConnection()
        log.User = user
        log.Duration = duration
        log.TxBytes = txBytes
        log.RxBytes = rxBytes
        return addEventItem(log, calSize)
    }

    fun addModemStatus(powerMode: PowerModeEnum, signalCSQ: Int, signaldBm: Int, calSize: Boolean = true): Int {
        val log = ModemStatus()
        log.PowerMode = powerMode
        log.SignalCSQ = signalCSQ
        log.SignaldBm = signaldBm
        return addEventItem(log, calSize)
    }

    fun addCutFailure(totalTicketsPrinted: Long, totalRetries: Long, retriesForLastTicket: Long, calSize: Boolean = true): Int {
        val log = CutFailure()
        log.TotalTicketsPrinted = totalTicketsPrinted
        log.TotalRetries = totalRetries
        log.RetriesForLastTicket = retriesForLastTicket
        return addEventItem(log, calSize)
    }

    fun addPenaltyTransaction(transactionSerialNumber: Long,
                              amountCharged: Long,
                              amountPaid: Long,
                              tariffCode: String,
                              penaltyCode: String,
                              calSize: Boolean = true): Int {
        val log = PenaltyTransaction()
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountCharged = amountCharged
        log.AmountPaid = amountPaid
        log.TariffCode = tariffCode
        log.PenaltyCode = penaltyCode
        return addEventItem(log, calSize)
    }

    fun addCallReason(sessionSerialNo: Long,
                      applicationStart: Boolean,
                      statusFlagChange: Boolean,
                      scheduledCall: Boolean,
                      backOfficeCall: Boolean,
                      retryAfterBusy: Boolean,
                      retryAfterFailure: Boolean,
                      testCall: Boolean,
                      forcedCall: Boolean,
                      immediateJob: Boolean,
                      calSize: Boolean = true): Int {
        val log = CallReason()
        log.SessionSerialNo = sessionSerialNo
        log.ApplicationStart = applicationStart
        log.StatusFlagChange = statusFlagChange
        log.ScheduledCall = scheduledCall
        log.BackOfficeCall = backOfficeCall
        log.RetryAfterBusy = retryAfterBusy
        log.RetryAfterFailure = retryAfterFailure
        log.TestCall = testCall
        log.ForcedCall = forcedCall
        log.ImmediateJob = immediateJob
        return addEventItem(log, calSize)
    }

    fun addBackOfficeResp(bor: BOR, calSize: Boolean = true): Int {
        val log = BackOfficeResp()
        log.Data.SerialNo = bor.SerialNo
        log.Data.Response = bor.Response
        return addEventItem(log, calSize)
    }

    fun addBackOfficeCmd(boc: BOC = BOC(), calSize: Boolean = true): Int {
        val log = BackOfficeCmd()
        log.Data.SerialNo = boc.SerialNo ?: 0L
        log.Data.Command = boc.Command
        log.Data.NumberPar1 = boc.NumberPar1 ?: 0L
        log.Data.StringPar1 = boc.StringPar1 ?: ""
        return addEventItem(log, calSize)
    }

    fun addFile(file: File, calSize: Boolean = true): Int {
        val extension = file.extension.uppercase()
        val log = when (extension) {
            APP::class.simpleName -> APP()
            CFG::class.simpleName -> CFG()
            TRF::class.simpleName -> TRF()
            DKL::class.simpleName -> DKL()
            HTL::class.simpleName -> HTL()
            CLT::class.simpleName -> CLT()
            PIC::class.simpleName -> PIC()
            BL3::class.simpleName -> BL3()
            LUL::class.simpleName -> LUL()
            else -> return 0
        }
        val entry = FileMxdUtils.file2Entry(file) ?: return 0
        log.File.setFile(entry)
        return addEventItem(log, calSize)
    }

    fun addPsuStatistics(sampleCount: Int,
                         mainsOnSampleCount: Int,
                         solarOnSampleCount: Int,
//                         currentAcc: PSU_STATISTICS_AV_MIN_MAX,
//                         voltageAcc: PSU_STATISTICS_AV_MIN_MAX,
//                         temperature: PSU_STATISTICS_AV_MIN_MAX,
                         accumulator1: EVENT_LOG_PSU_ACCUMULATOR,
                         accumulator2: EVENT_LOG_PSU_ACCUMULATOR,
                         calSize: Boolean = true): Int {
        val log = PsuStatistics()
        log.SampleCount = sampleCount
        log.MainsOnSampleCount = mainsOnSampleCount
        log.SolarOnSampleCount = solarOnSampleCount
//        log.CurrentAcc.setValue(currentAcc)
//        log.VoltageAcc.setValue(voltageAcc)
//        log.Temperature.setValue(temperature)
        log.Accumulator1.setValue(accumulator1)
        log.Accumulator2.setValue(accumulator2)
        return addEventItem(log, calSize)
    }

    fun addLock(lockType: LMCLockTypeEnum,
                keyPresentationTime: Long,
                keyNumber: Long,
                succeeded: Boolean,
                lockStatus: LMCLockStatusEnum,
                calSize: Boolean = true): Int {
        val log = Lock()
        log.LockType = lockType
        log.KeyPresentationTime = keyPresentationTime
        log.KeyNumber = keyNumber
        log.Succeeded = succeeded
        log.LockStatus = lockStatus
        return addEventItem(log, calSize)
    }

    fun addTestToken(action: TokenActionEnum, calSize: Boolean = true): Int {
        val log = TestToken()
        log.Action = action
        return addEventItem(log, calSize)
    }

    fun addRechargeLimitChange(expiry: Long, quantity: Long, calSize: Boolean = true): Int {
        val log = RechargeLimitChange()
        log.Expiry = expiry
        log.Quantity = quantity
        return addEventItem(log, calSize)
    }

    fun addTmsCall(cardReaderType: String,
                   startTime: Long,
                   duration: Long,
                   status: CardProcessStatusEnum,
                   calSize: Boolean = true): Int {
        val log = TmsCall()
        log.CardReaderType = cardReaderType
        log.StartTime = startTime
        log.Duration = duration
        log.Status = status
        return addEventItem(log, calSize)
    }

    fun addSpaceSystemAuditPeriodEnd(triggerType: EndAuditPeriodEnum,
                                     triggerSequenceNumber: Long,
                                     auditNo: Long,
                                     startTime: Long,
                                     endTime: Long,
                                     zones: List<AUDIT_SPACE_SYSTEM_ZONE>,
                                     calSize: Boolean = true): Int {
        val log = SpaceSystemAuditPeriodEnd()
        log.TriggerType = triggerType
        log.TriggerSequenceNumber = triggerSequenceNumber
        log.Data.AuditNo = auditNo
        log.Data.StartTime = startTime
        log.Data.EndTime = endTime
        log.Data.nZones = zones.size
        log.Data.Zones.addAll(zones)
        return addEventItem(log, calSize)
    }

    fun addCardAuditPeriodEnd(triggerType: EndAuditPeriodEnum,
                              triggerSequenceNumber: Long,
                              auditNo: Long,
                              startTime: Long,
                              endTime: Long,
                              cumDebitTransactions: Long,
                              cumDebitAmount: Long,
                              cumCreditTransactions: Long,
                              cumCreditAmount: Long,
                              cardSystem: List<AUDIT_CARD_SYSTEM>,
                              calSize: Boolean = true): Int {
        val log = CardAuditPeriodEnd()
        log.TriggerType = triggerType
        log.TriggerSequenceNumber = triggerSequenceNumber
        log.Data.AuditNo = auditNo
        log.Data.StartTime = startTime
        log.Data.EndTime = endTime
        log.Data.CumDebitTransactions = cumDebitTransactions
        log.Data.CumDebitAmount = cumDebitAmount
        log.Data.CumCreditTransactions = cumCreditTransactions
        log.Data.CumCreditAmount = cumCreditAmount
        log.Data.CardSystem.addAll(cardSystem)
        return addEventItem(log, calSize)
    }

    fun addCardCollection(triggerType: EndAuditPeriodEnum, cardType: CardSystemTypesEnum, calSize: Boolean = true): Int {
        val log = CardCollection()
        log.TriggerType = triggerType
        log.CardType = cardType
        return addEventItem(log, calSize)
    }

    fun addTicketStock(timeChanged: Long,
                       oldRollLength: Long,
                       ticketsUsed: Long,
                       newRollLength: Long,
                       printer: TicketPrinterEnum,
                       calSize: Boolean = true): Int {
        val log = TicketStock()
        log.Printer = printer
        log.TimeChanged = timeChanged
        log.OldRollLength = oldRollLength
        log.TicketsUsed = ticketsUsed
        log.NewRollLength = newRollLength
        return addEventItem(log, calSize)
    }

    fun addKeyPresented(keyNumber: Long,
                        keyType: DKMKeyTypeEnum,
                        accepted: Boolean,
                        presentationTime: Long,
                        serialNo: Long,
                        name: String,
                        calSize: Boolean = true): Int {
        val log = KeyPresented()
        log.KeyNumber = keyNumber
        log.KeyType = keyType
        log.Accepted = accepted
        log.PresentationTime = presentationTime
        log.SerialNo = serialNo
        log.Name = name
        return addEventItem(log, calSize)
    }

    fun addCoinDebit(transactionSerialNumber: Long, amountPaid: Long, calSize: Boolean = true): Int {
        val log = CoinDebit()
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountPaid = amountPaid
        return addEventItem(log, calSize)
    }

    fun addNoteDebit(transactionSerialNumber: Long, amountPaid: Long, calSize: Boolean = true): Int {
        val log = NoteDebit()
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountPaid = amountPaid
        return addEventItem(log, calSize)
    }

    fun addCoinUnrefunded(transactionSerialNumber: Long, amountPaid: Long, calSize: Boolean = true): Int {
        val log = CoinUnrefunded()
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountPaid = amountPaid
        return addEventItem(log, calSize)
    }

    fun addNoteUnrefunded(transactionSerialNumber: Long, amountPaid: Long, calSize: Boolean = true): Int {
        val log = NoteUnrefunded()
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountPaid = amountPaid
        return addEventItem(log, calSize)
    }

    fun addCardUnrefunded(transactionSerialNumber: Long,
                     cardType: CardSystemTypesEnum,
                     cardNumber: String,
                     iso4217Code: CurrencyIso4217Enum,
                     authorisationCode: String,
                     status: CardProcessStatusEnum,
                     amountPaid: Long,
                     balance: Long,
                     terminalId: String,
                     loyaltyID: String,
                     calSize: Boolean = true): Int {
        val log = CardUnrefunded()
        log.TransactionSerialNumber = transactionSerialNumber
        log.CardType = cardType
        log.CardNumber = cardNumber
        log.Iso4217Code = iso4217Code
        log.AuthorisationCode = authorisationCode
        log.Status = status
        log.AmountPaid = amountPaid
        log.Balance = balance
        log.TerminalId = terminalId
        log.LoyaltyID = loyaltyID
        return addEventItem(log, calSize)
    }

    fun addCoin(className: String, transactionSerialNumber: Long, amountPaid: Long, calSize: Boolean = true): Int {
        val log = when (className) {
            CoinDebit::class.simpleName -> CoinDebit()
            NoteDebit::class.simpleName -> NoteDebit()
            CoinUnrefunded::class.simpleName -> CoinUnrefunded()
            NoteUnrefunded::class.simpleName -> NoteUnrefunded()
            else -> return 0
        }
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountPaid = amountPaid
        return addEventItem(log, calSize)
    }

    fun addCard(className: String,
                transactionSerialNumber: Long,
                cardType: CardSystemTypesEnum,
                cardNumber: String,
                iso4217Code: CurrencyIso4217Enum,
                authorisationCode: String,
                status: CardProcessStatusEnum,
                amountCredited: Long,
                balance: Long,
                terminalId: String,
                loyaltyID: String,
                calSize: Boolean = true): Int {
        val log = when (className) {
            CardRefund::class.simpleName -> CardRefund()
            CardCredit::class.simpleName -> CardCredit()
            else -> return 0
        }
        log.TransactionSerialNumber = transactionSerialNumber
        log.CardType = cardType
        log.CardNumber = cardNumber
        log.Iso4217Code = iso4217Code
        log.AuthorisationCode = authorisationCode
        log.Status = status
        log.AmountCredited = amountCredited
        log.Balance = balance
        log.TerminalId = terminalId
        log.LoyaltyID = loyaltyID
        return addEventItem(log, calSize)
    }

    fun addCardDebit(transactionSerialNumber: Long,
                     cardType: CardSystemTypesEnum,
                     cardNumber: String,
                     iso4217Code: CurrencyIso4217Enum,
                     authorisationCode: String,
                     status: CardProcessStatusEnum,
                     amountPaid: Long,
                     balance: Long,
                     terminalId: String,
                     loyaltyID: String,
                     calSize: Boolean = true): Int {
        val log = CardDebit()
        log.TransactionSerialNumber = transactionSerialNumber
        log.CardType = cardType
        log.CardNumber = cardNumber
        log.Iso4217Code = iso4217Code
        log.AuthorisationCode = authorisationCode
        log.Status = status
        log.AmountPaid = amountPaid
        log.Balance = balance
        log.TerminalId = terminalId
        log.LoyaltyID = loyaltyID
        return addEventItem(log, calSize)
    }

    fun addCardNonPayment(transactionSerialNumber: Long,
                          cardType: CardSystemTypesEnum,
                          cardNumber: String,
                          status: CardProcessStatusEnum,
                          calSize: Boolean = true): Int {
        val log = CardNonPayment()
        log.TransactionSerialNumber = transactionSerialNumber
        log.CardType = cardType
        log.CardNumber = cardNumber
        log.Status = status
        return addEventItem(log, calSize)
    }

    fun addTransportTransaction(transactionSerialNumber: Long,
                                amountCharged: Long,
                                startTime: Long,
                                endTime: Long,
                                numberOfPassengers: Int,
                                tariffCode: String,
                                calSize: Boolean = true): Int {
        val log = TransportTransaction()
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountCharged = amountCharged
        log.StartTime = startTime
        log.EndTime = endTime
        log.NumberOfPassengers = numberOfPassengers
        log.TariffCode = tariffCode
        return addEventItem(log, calSize)
    }

    fun addTransaction(transactionType: TransactionTypeEnum,
                       transactionSerialNumber: Long,
                       amountCharged: Long,
                       amountPaid: Long,
                       tariffCode: String,
                       startTime: Long,
                       endTime: Long,
                       registrationNumber: String,
                       spaceNumber: Long,
                       zoneId: Long,
                       vrmSelected: VrmSelectTypeEnum,
                       concessionEntered: ConcessionEnteredTypeEnum,
                       concessionCode: String,
                       loyaltyID: String,
                       calSize: Boolean = true): Int {
        val log = Transaction()
        log.TransactionType = transactionType
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountCharged = amountCharged
        log.AmountPaid = amountPaid
        log.TariffCode = tariffCode
        log.StartTime = startTime
        log.EndTime = endTime
        log.RegistrationNumber = registrationNumber
        log.SpaceNumber = spaceNumber
        log.ZoneId = zoneId
        log.VrmSelected = vrmSelected
        log.ConcessionEntered = concessionEntered
        log.ConcessionCode = concessionCode
        log.LoyaltyID = loyaltyID
        return addEventItem(log, calSize)
    }

    fun addStatusFlagChange(set: Boolean,
                            dev: Int,
                            flag: Int,
                            level: FlagLevelEnum,
                            devDesc: String,
                            flagDesc: String, calSize: Boolean = true): Int {
        val log = StatusFlagChange()
        log.Set = set
        log.Dev = dev
        log.Flag = flag
        log.Level = level
        log.DevDesc = devDesc
        log.FlagDesc = flagDesc
        return addEventItem(log, calSize)
    }

    fun addExceptionPostmortem(crashReason: CrashReasonEnum,
                               registers: List<Long>,
                               psr: Long,
                               task: Long,
                               taskStackStart: Long,
                               taskStackEnd: Long,
                               taskName: String,
                               calSize: Boolean = true): Int {
        val log = ExceptionPostmortem()
        log.CrashReason = crashReason
        log.Registers.addAll(registers)
        log.Psr = psr
        log.Task = task
        log.TaskStackStart = taskStackStart
        log.TaskStackEnd = taskStackEnd
        log.TaskName = taskName
        return addEventItem(log, calSize)
    }

    fun addExceptionStackDump(exceptionType: String, message: String, stackTrace: String, calSize: Boolean = true): Int {
        val log = ExceptionStackDump()
        log.ExceptionType = exceptionType
        log.Message = message
        log.StackTrace = stackTrace
        return addEventItem(log, calSize)
    }

    fun addStartup(startupReason: StartupReasonEnum, accumulatorVoltage: Int, calSize: Boolean = true): Int {
        val log = Startup()
        log.StartupReason = startupReason
        log.AccumulatorVoltage = accumulatorVoltage
        return addEventItem(log, calSize)
    }

    fun addTokenDebit(transactionSerialNumber: Long,
                      amountPaid: Long,
                      tokenInfo: List<AUDIT_TOKEN_TRANS_INFO>,
                      calSize: Boolean = true): Int {
        val log = TokenDebit()
        log.TransactionSerialNumber = transactionSerialNumber
        log.AmountPaid = amountPaid
        log.TokenInfo.addAll(tokenInfo)
        return addEventItem(log, calSize)
    }

    fun addCashBoxRemoved(boxType: BoxTypeEnum, data: AUDIT_CASH_PERIOD, calSize: Boolean = true): Int {
        val log = CashBoxRemoved()
        log.BoxType = boxType
        log.Data = data
        return addEventItem(log, calSize)
    }

    fun addTransactionAuditPeriodEnd(triggerType: EndAuditPeriodEnum,
                                     triggerSequenceNumber: Long,
                                     data: AUDIT_TRANSACTION_PERIOD,
                                     calSize: Boolean = true): Int {
        val log = TransactionAuditPeriodEnd()
        log.TriggerType = triggerType
        log.TriggerSequenceNumber = triggerSequenceNumber
        log.Data = data
        return addEventItem(log, calSize)
    }

    fun addPsuStatus(status: TEMP_PSU_EXT, calSize: Boolean = true): Int {
        val log = PsuStatus()
        log.Status = status
        return addEventItem(log, calSize)
    }

    fun addAPP(file: Entry, calSize: Boolean = true): Int {
        val log = APP()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addCFG(file: Entry, calSize: Boolean = true): Int {
        val log = CFG()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addTRF(file: Entry, calSize: Boolean = true): Int {
        val log = TRF()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addDKL(file: Entry, calSize: Boolean = true): Int {
        val log = DKL()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addHTL(file: Entry, calSize: Boolean = true): Int {
        val log = HTL()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addCLT(file: Entry, calSize: Boolean = true): Int {
        val log = CLT()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addPIC(file: Entry, calSize: Boolean = true): Int {
        val log = PIC()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addBL3(file: Entry, calSize: Boolean = true): Int {
        val log = BL3()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addLUL(file: Entry, calSize: Boolean = true): Int {
        val log = LUL()
        log.File = file
        return addEventItem(log, calSize)
    }

    fun addBarCode(transactionSerialNumber: Long, barcodeID: String, calSize: Boolean = true): Int {
        val log = BarCode()
        log.TransactionSerialNumber = transactionSerialNumber
        log.BarcodeID = barcodeID
        return addEventItem(log, calSize)
    }

    fun addVoucher(transactionSerialNumber: Long,
                   voucherType: VoucherSystemTypesEnum,
                   voucherNumber: String,
                   authorisationCode: String,
                   status: VoucherProcessStatusEnum,
                   amountPaid: Long,
                   isRefund: Boolean,
                   calSize: Boolean = true): Int {
        val log = Voucher()
        log.TransactionSerialNumber = transactionSerialNumber
        log.VoucherType = voucherType
        log.VoucherNumber = voucherNumber
        log.AuthorisationCode = authorisationCode
        log.Status = status
        log.AmountPaid = amountPaid
        log.IsRefund = isRefund
        return addEventItem(log, calSize)
    }

    fun addOfflineFileTransferStart(calSize: Boolean = true): Int {
        val log = OfflineFileTransferStart()
        return addEventItem(log, calSize)
    }

    fun addOfflineFileTransferEnd(result: OfflineFileTransferResultEnum, calSize: Boolean = true): Int {
        val log = OfflineFileTransferEnd()
        log.Result = result
        return addEventItem(log, calSize)
    }

    fun addUiStateResult(state: UiTxnStateEnum,
                         transactionSerialNumber: Long,
                         startTime: Instant,
                         endTime: Instant,
                         language: Languages,
                         registrationNumber: String,
                         stateHistory: String,
                         calSize: Boolean = true): Int {
        val log = UiStateResult()
        log.State = state
        log.TransactionSerialNumber = transactionSerialNumber
        log.StartTime = startTime.epochSecond
        log.EndTime = endTime.epochSecond
        log.Language = language.Language
        log.RegistrationNumber = registrationNumber
        log.StateHistory = stateHistory
        return addEventItem(log, calSize)
    }

    fun addX56PrintResult(transactionSerialNumber: Long,
                          printCmdSeqNumber: Long,
                          printResult: Int,
                          paperControlError: Int,
                          paperControlStatus: Int,
                          printerStatus: Long,
                          calSize: Boolean = true): Int {
        val log = X56PrintResult()
        log.TransactionSerialNumber = transactionSerialNumber
        log.PrintCmdSeqNumber = printCmdSeqNumber
        log.PrintResult = printResult
        log.PaperControlError = paperControlError
        log.PaperControlStatus = paperControlStatus
        log.PrinterStatus = printerStatus
        return addEventItem(log, calSize)
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////
    private val synAny = Any()
    private val listInsertPair = Vector<Pair<String, String>>()
    private fun insert(any: Any, className: String?): Int {
        MLog.d("ELGData", "insert: $any, className:$className")
        try {
            val fieldSQL = "json, className"
            val bytes = JsonUtils.toJson(any).toByteArray()
            val base64 = Base64.encode(bytes, Base64.NO_WRAP)
            val json = String(base64)
            val valueSQL = "'$json', '$className'"
            var result = false
            try {
                result = SQLiteManager.getInstance().insert(null, SQLITE_TABLE_NAME, fieldSQL, valueSQL)
            }catch (e: Exception){
                MLog.e("ELGData", "insert SQL exception: ${e.stackTraceToString()}")
            }
            if (!result){
                listInsertPair.add(Pair(fieldSQL, valueSQL))
            }
            val size = listInsertPair.size
            MLog.d("ELGData", "insert: $size([$fieldSQL],[$valueSQL])")
//                KLog.d("sendAuditElg", "insert: $size")
            return size
        } catch (e: Exception) {
            MLog.e("ELGData", "insert exception: ${e.stackTraceToString()}")
            return 0
        }
    }
    private fun delete(): Boolean {
        isDropping = true
        val result = SQLiteManager.getInstance().delete(null, SQLITE_TABLE_NAME)
//        listInsertPair.clear()
        SystemClock.sleep(100)
        MLog.d("ELGData", "delete: $result")
        isDropping = false
        return result
    }
    fun fileWriteOK() {
        val result = delete()
        MLog.d("[SensorFlow]ELGData", "fileWriteOk - deleteTable: $result")
//        val fields = Hashtable<String, String>()
//        fields["json"] = String::class.simpleName
//        fields["className"] = String::class.simpleName
        isDropping = true
        val deleteFolder = SQLiteManager.getInstance().deleteFolder()
//        val create = SQLiteManager.getInstance().create(null, SQLITE_TABLE_NAME, fields)
        isDropping = false
        MLog.d("[SensorFlow]ELGData", "fireWriteOk - deleteFolder: $deleteFolder")
    }

    private inline fun <reified T: ElgEntry> addFromSql(elg: SQLiteELG) {
        JsonUtils.fromJson(elg.json, T::class.java)?.let { addEventItem(it) }
    }

    private fun createTable() {
        MLog.i("ELGData", "createTable start")
        try {
            val fields = Hashtable<String, String>()
            fields["json"] = String::class.simpleName
            fields["className"] = String::class.simpleName
            isFileOperating = true
            if (SQLiteManager.getInstance().create(null, SQLITE_TABLE_NAME, fields)) {
                startInsert()
                MLog.d("ELGData", "createTable: true")
                @SuppressLint("Range")
                val list = SQLiteManager.getInstance().query(null, SQLITE_TABLE_NAME
                ) { cursor ->
                    val sqliteELG = SQLiteELG()
                    sqliteELG.id = cursor.getInt(cursor.getColumnIndex("id"))
                    val base64 = cursor.getString(cursor.getColumnIndex("json"))
                    val bytes = Base64.decode(base64, Base64.NO_WRAP)
                    sqliteELG.json = String(bytes)
                    MLog.d("ELGData", "onFoundCursor: ${sqliteELG.json}")
                    sqliteELG.className = cursor.getString(cursor.getColumnIndex("className"))
                    sqliteELG
                }
                MLog.d("ELGData", "query: ${list.size}")
                MLog.d("ELGData", "query-list ${JsonUtils.toJson(list)}")
                if (list.size > 0) {
                    isDropping = true
                    val deleteFolder = SQLiteManager.getInstance().deleteFolder()
                    val create = SQLiteManager.getInstance().create(null, SQLITE_TABLE_NAME, fields)
                    MLog.e("ELGData", "createTable - deleteFolder: $deleteFolder, create: $create")
                    isDropping = false
                    if (deleteFolder && create) {
//                    if (delete()/* && SQLiteManager.getInstance().create(null, SQLITE_TABLE_NAME, fields)*/) {
                        for (sqliteELG in list) {
                            when (sqliteELG.className) {
                                Header::class.simpleName -> {
                                    val db = JsonUtils.fromJson(sqliteELG.json, Header::class.java)
                                    if (db != null) {
                                        header = db
                                    }
                                }

                                    Startup::class.simpleName -> addFromSql<Startup>(sqliteELG)
                                    ExceptionPostmortem::class.simpleName -> addFromSql<ExceptionPostmortem>(sqliteELG)
                                    ExceptionStackDump::class.simpleName -> addFromSql<ExceptionStackDump>(sqliteELG)
                                    StatusFlagChange::class.simpleName -> addFromSql<StatusFlagChange>(sqliteELG)
                                    Transaction::class.simpleName -> addFromSql<Transaction>(sqliteELG)
                                    TransportTransaction::class.simpleName -> addFromSql<TransportTransaction>(sqliteELG)
                                    CardNonPayment::class.simpleName -> addFromSql<CardNonPayment>(sqliteELG)
                                    CardDebit::class.simpleName -> addFromSql<CardDebit>(sqliteELG)
                                    CardCredit::class.simpleName -> addFromSql<CardCredit>(sqliteELG)
                                    CardRefund::class.simpleName -> addFromSql<CardRefund>(sqliteELG)
                                    CoinDebit::class.simpleName -> addFromSql<CoinDebit>(sqliteELG)
                                    NoteDebit::class.simpleName -> addFromSql<NoteDebit>(sqliteELG)
                                    TokenDebit::class.simpleName -> addFromSql<TokenDebit>(sqliteELG)
                                    CoinUnrefunded::class.simpleName -> addFromSql<CoinUnrefunded>(sqliteELG)
                                    NoteUnrefunded::class.simpleName -> addFromSql<NoteUnrefunded>(sqliteELG)
                                    CardUnrefunded::class.simpleName -> addFromSql<CardUnrefunded>(sqliteELG)
                                    KeyPresented::class.simpleName -> addFromSql<KeyPresented>(sqliteELG)
                                    TicketStock::class.simpleName -> addFromSql<TicketStock>(sqliteELG)
                                    CardCollection::class.simpleName -> addFromSql<CardCollection>(sqliteELG)
                                    CashBoxRemoved::class.simpleName -> addFromSql<CashBoxRemoved>(sqliteELG)
                                    CardAuditPeriodEnd::class.simpleName -> addFromSql<CardAuditPeriodEnd>(sqliteELG)
                                    TransactionAuditPeriodEnd::class.simpleName -> addFromSql<TransactionAuditPeriodEnd>(sqliteELG)
                                    SpaceSystemAuditPeriodEnd::class.simpleName -> addFromSql<SpaceSystemAuditPeriodEnd>(sqliteELG)
                                    TmsCall::class.simpleName -> addFromSql<TmsCall>(sqliteELG)
                                    RechargeLimitChange::class.simpleName -> addFromSql<RechargeLimitChange>(sqliteELG)
                                    TestToken::class.simpleName -> addFromSql<TestToken>(sqliteELG)
                                    Lock::class.simpleName -> addFromSql<Lock>(sqliteELG)
                                    PsuStatistics::class.simpleName -> addFromSql<PsuStatistics>(sqliteELG)
                                    PsuStatus::class.simpleName -> addFromSql<PsuStatus>(sqliteELG)
                                    APP::class.simpleName -> addFromSql<APP>(sqliteELG)
                                    CFG::class.simpleName -> addFromSql<CFG>(sqliteELG)
                                    TRF::class.simpleName -> addFromSql<TRF>(sqliteELG)
                                    DKL::class.simpleName -> addFromSql<DKL>(sqliteELG)
                                    HTL::class.simpleName -> addFromSql<HTL>(sqliteELG)
                                    CLT::class.simpleName -> addFromSql<CLT>(sqliteELG)
                                    PIC::class.simpleName -> addFromSql<PIC>(sqliteELG)
                                    BL3::class.simpleName -> addFromSql<BL3>(sqliteELG)
                                    LUL::class.simpleName -> addFromSql<LUL>(sqliteELG)
                                    BackOfficeCmd::class.simpleName -> addFromSql<BackOfficeCmd>(sqliteELG)
                                    BackOfficeResp::class.simpleName -> addFromSql<BackOfficeResp>(sqliteELG)
                                    CallReason::class.simpleName -> addFromSql<CallReason>(sqliteELG)
                                    PenaltyTransaction::class.simpleName -> addFromSql<PenaltyTransaction>(sqliteELG)
                                    ModemStatus::class.simpleName -> addFromSql<ModemStatus>(sqliteELG)
                                    TcpIpConnection::class.simpleName -> addFromSql<TcpIpConnection>(sqliteELG)
                                    AnprOfflineDbRecordPurge::class.simpleName -> addFromSql<AnprOfflineDbRecordPurge>(sqliteELG)
                                    BarCode::class.simpleName -> addFromSql<BarCode>(sqliteELG)
                                    VESCatSelect::class.simpleName -> addFromSql<VESCatSelect>(sqliteELG)
                                    Voucher::class.simpleName -> addFromSql<Voucher>(sqliteELG)
                                    OfflineFileTransferStart::class.simpleName -> addFromSql<OfflineFileTransferStart>(sqliteELG)
                                    OfflineFileTransferEnd::class.simpleName -> addFromSql<OfflineFileTransferEnd>(sqliteELG)
                                    UiStateResult::class.simpleName -> addFromSql<UiStateResult>(sqliteELG)
                                    X56PrintResult::class.simpleName -> addFromSql<X56PrintResult>(sqliteELG)
                                    CutFailure::class.simpleName -> addFromSql<CutFailure>(sqliteELG)
                                    OtherTransaction::class.simpleName -> addFromSql<OtherTransaction>(sqliteELG)
                            }
                        }
                    } else {
                        MLog.e("ELGData", "delete: fail")
                    }
                }
            } else {
                MLog.e("ELGData", "createTable: fail")
            }
        } catch (e: Exception) {
            MLog.e("ELGData", "createTable exception: ${e.stackTraceToString()}")
        }finally {
            isFileOperating = false
        }
        MLog.e("ELGData", "createTable finish")
    }

    fun getEventItems(): List<ElgEntry> {
        return eventItems
    }

    private var isRunningInsert = false
    private var isDropping = false
    var isFileOperating = false
    fun startInsert() {
        MLog.i("ELGData", "startInsert - isRunningInsert: $isRunningInsert")
        if (isRunningInsert) {
            return
        }
        isRunningInsert = true
        runThread {
            MLog.i("ELGData", "run insert size: ${listInsertPair.size}")
            while (isRunningInsert) {
                SystemClock.sleep(100)
                if (listInsertPair.isEmpty()) {
                    continue
                }
                if (isDropping) {
                    continue
                }
                isFileOperating = true
                synchronized(synAny) {
                    try {
                        val pair = listInsertPair[0]
                        val fieldSQL = pair.first
                        val valueSQL = pair.second
                        val result = SQLiteManager.getInstance()
                            .insert(null, SQLITE_TABLE_NAME, fieldSQL, valueSQL)
                        if (result) {
                            listInsertPair.removeAt(0)
//                            KLog.d("sendAuditElg", "removeAt: ${listInsertPair.size}")
                        }else{
                            MLog.e("ELGData", "insert fail - first: $fieldSQL, second: $valueSQL")
                        }
                    } catch (e: Exception) {
                        MLog.e("ELGData", "insertException: ${e.stackTraceToString()}")
                    }
                }
                isFileOperating = false
            }
        }
    }
    fun stopInsert() {
        MLog.i("ELGData", "stopInsert")
        isRunningInsert = false
    }

    fun writeDataSync(){
        MLog.i("ELGData","writeDataSync - listInsertPair.size:${listInsertPair.size}")
        if (listInsertPair.size == 0){
            return
        }
        isFileOperating = true
        try {
            val vector = Vector<Pair<String, String>>()
            for (pair in listInsertPair){
                val fieldSQL = pair.first
                val valueSQL = pair.second
                try {
                    val result = SQLiteManager.getInstance()
                        .insert(null, SQLITE_TABLE_NAME, fieldSQL, valueSQL)
                    if (result) {
                        vector.add(pair)
                    }
                }catch (e: Exception){
                    e.printStackTrace()
                }
            }
            MLog.d("ELGData", "remove-before-size: ${listInsertPair.size}")
            listInsertPair.removeAll(vector)
            MLog.d("ELGData", "remove-after-size: ${listInsertPair.size}")
        } catch (e: Exception) {
            MLog.e("ELGData", "insertException: ${e.stackTraceToString()}")
        }
        isFileOperating = false
    }
}
