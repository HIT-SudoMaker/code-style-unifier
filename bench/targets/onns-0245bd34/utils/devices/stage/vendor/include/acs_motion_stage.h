//////////////////////////////////////////////////////////////////////////////////////////////////
//  
// ACS Motion Control Ltd.
// Copyright © 1999 - 2018. All Rights Reserved.
//
// PROJECT			:    SPiiPlus 
// SUBSYSTEM		:    SPiiPlus C Library
// FILE				:	 ACSC.h
// VERSION			:    6.66.0.0 

// OVERVIEW
// ========
//
// SPiiPlus C Library export functions definition
// 
//////////////////////////////////////////////////////////////////////////////////////////////////

#ifndef _ACSC_H_
#define _ACSC_H_

#if defined(WIN32) && !defined(UNDER_RTSS)
// Win32
#include <windows.h>
#include <Winsock.h>

#elif defined(WIN32) && defined(UNDER_RTSS)
// RTX
#include <windows.h>
#include <rtapi.h>
#endif




//////////////////////////////////////////////////////////////////////////////////////////////////
// General definitions
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_VER					0x6420000


#define ACSC_MAXCHANNEL				10			//Maximum number of communication channels
#define ACSC_INVALID				(HANDLE)-1	//Invalid communication handle 
#define ACSC_NONE					-1				
#define ACSC_INT_BINARY				4			//Size of the controller integer variable
#define ACSC_REAL_BINARY			8			//Size of the controller real variable
#define ACSC_FILE					-2
#define ACSC_DEFAULT_REMOTE_PORT	9999


#define ACSC_AXES_MAX_NUMBER		64			//Maximum number of supported axes
#define ACSC_BUFFERS_MAX_NUMBER		65			//Maximum number of supported buffers (including D-Buffer)
#define ACSC_SP_MAX_NUMBER			64			//Maximum number of supported Servo Processors (SP)
#define ACSC_DC_VAR_MAX_NUMBER		10			//Maximum number of variables to be collected by one command
#define ACSC_MAX_LINE				100000		//Maximum number of lines in program buffer
#define ACSC_COUNTERCLOCKWISE		1			//Counterclockwise rotation
#define ACSC_CLOCKWISE				-1			//Clockwise rotation
#define ACSC_POSITIVE_DIRECTION		1			//A move in positive direction
#define ACSC_NEGATIVE_DIRECTION		-1			//A move in negative direction

// for compatibility with the previous library
#define MAXCHANNEL					10				
			
// Set/Get configuration keys
#define ACSC_CONF_WORD1_KEY					1
#define ACSC_CONF_INT_EDGE_KEY				3
#define ACSC_CONF_ENCODER_KEY				4
#define ACSC_CONF_MFLAGS9_KEY				204
#define ACSC_CONF_DIGITAL_SOURCE_KEY		205
#define ACSC_CONF_SP_OUT_PINS_KEY			206
#define ACSC_CONF_OUT_KEY					29
#define ACSC_CONF_BRAKE_OUT_KEY				229

// System Information keys
#define ACSC_SYS_MODEL_KEY					1
#define ACSC_SYS_VERSION_KEY				2
#define ACSC_SYS_NBUFFERS_KEY				10
#define ACSC_SYS_DBUF_INDEX_KEY				11
#define ACSC_SYS_NAXES_KEY					13
#define ACSC_SYS_NNODES_KEY					14
#define ACSC_SYS_NDCCH_KEY					15
#define ACSC_SYS_ECAT_KEY					16


//////////////////////////////////////////////////////////////////////////////////////////////////
// ACSPL+ variables types
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_INT_TYPE						1	//Integer type of the variable (Decimal representation)
#define ACSC_REAL_TYPE						2	//Real type of the variable (Decimal representation)

//////////////////////////////////////////////////////////////////////////////////////////////////
// Represintation types of file stored variables
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_DEC_REAL_TYPE					8	 //Decimal representation of Real type variable
#define ACSC_DEC_INT_TYPE					4	 //Decimal representation of Integer type variable
#define ACSC_BIN_INT_TYPE					2	 //Binary representation of Integer type variable
#define ACSC_OCT_INT_TYPE					1	 //Octal representation of Integer type variable
#define ACSC_HEX_INT_TYPE 					16	 //Hexadecimal representation of Integer type variable

//////////////////////////////////////////////////////////////////////////////////////////////////
// Serial communication options
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_AUTO -1

//////////////////////////////////////////////////////////////////////////////////////////////////
// Ethernet communication options
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_SOCKET_DGRAM_PORT				700
#define ACSC_SOCKET_STREAM_PORT				701

//////////////////////////////////////////////////////////////////////////////////////////////////
// Old Axes Definitions
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_AXIS_X							0
#define ACSC_AXIS_Y							1
#define ACSC_AXIS_Z							2
#define ACSC_AXIS_T							3
#define ACSC_AXIS_A							4
#define ACSC_AXIS_B							5
#define ACSC_AXIS_C							6
#define ACSC_AXIS_D							7

//////////////////////////////////////////////////////////////////////////////////////////////////
// New Axes Definitions
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_PAR_ALL						-2
#define ACSC_SYSTEM							-3
#define ACSC_AXIS_0							0
#define ACSC_AXIS_1							1
#define ACSC_AXIS_2							2
#define ACSC_AXIS_3							3
#define ACSC_AXIS_4							4
#define ACSC_AXIS_5							5
#define ACSC_AXIS_6							6
#define ACSC_AXIS_7							7
#define ACSC_AXIS_8							8
#define ACSC_AXIS_9							9
#define ACSC_AXIS_10						10
#define ACSC_AXIS_11						11
#define ACSC_AXIS_12						12
#define ACSC_AXIS_13						13
#define ACSC_AXIS_14						14
#define ACSC_AXIS_15						15
#define ACSC_AXIS_16						16
#define ACSC_AXIS_17						17
#define ACSC_AXIS_18						18
#define ACSC_AXIS_19						19
#define ACSC_AXIS_20						20
#define ACSC_AXIS_21						21
#define ACSC_AXIS_22						22
#define ACSC_AXIS_23						23
#define ACSC_AXIS_24						24
#define ACSC_AXIS_25						25
#define ACSC_AXIS_26						26
#define ACSC_AXIS_27						27
#define ACSC_AXIS_28						28
#define ACSC_AXIS_29						29
#define ACSC_AXIS_30						30
#define ACSC_AXIS_31						31
#define ACSC_AXIS_32						32
#define ACSC_AXIS_33						33
#define ACSC_AXIS_34						34
#define ACSC_AXIS_35						35
#define ACSC_AXIS_36						36
#define ACSC_AXIS_37						37
#define ACSC_AXIS_38						38
#define ACSC_AXIS_39						39
#define ACSC_AXIS_40						40
#define ACSC_AXIS_41						41
#define ACSC_AXIS_42						42
#define ACSC_AXIS_43						43
#define ACSC_AXIS_44						44
#define ACSC_AXIS_45						45
#define ACSC_AXIS_46						46
#define ACSC_AXIS_47						47
#define ACSC_AXIS_48						48
#define ACSC_AXIS_49						49
#define ACSC_AXIS_50						50
#define ACSC_AXIS_51						51
#define ACSC_AXIS_52						52
#define ACSC_AXIS_53						53
#define ACSC_AXIS_54						54
#define ACSC_AXIS_55						55
#define ACSC_AXIS_56						56
#define ACSC_AXIS_57						57
#define ACSC_AXIS_58						58
#define ACSC_AXIS_59						59
#define ACSC_AXIS_60						60
#define ACSC_AXIS_61						61
#define ACSC_AXIS_62						62
#define ACSC_AXIS_63						63

//////////////////////////////////////////////////////////////////////////////////////////////////
// Buffers Definitions
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_BUFFER_ALL						-2
#define ACSC_BUFFER_0						0
#define ACSC_BUFFER_1						1
#define ACSC_BUFFER_2						2
#define ACSC_BUFFER_3						3
#define ACSC_BUFFER_4						4
#define ACSC_BUFFER_5						5
#define ACSC_BUFFER_6						6
#define ACSC_BUFFER_7						7
#define ACSC_BUFFER_8						8
#define ACSC_BUFFER_9						9
#define ACSC_BUFFER_10						10
#define ACSC_BUFFER_11						11
#define ACSC_BUFFER_12						12
#define ACSC_BUFFER_13						13
#define ACSC_BUFFER_14						14
#define ACSC_BUFFER_15						15
#define ACSC_BUFFER_16						16
#define ACSC_BUFFER_17						17
#define ACSC_BUFFER_18						18
#define ACSC_BUFFER_19						19
#define ACSC_BUFFER_20						20
#define ACSC_BUFFER_21						21
#define ACSC_BUFFER_22						22
#define ACSC_BUFFER_23						23
#define ACSC_BUFFER_24						24
#define ACSC_BUFFER_25						25
#define ACSC_BUFFER_26						26
#define ACSC_BUFFER_27						27
#define ACSC_BUFFER_28						28
#define ACSC_BUFFER_29						29
#define ACSC_BUFFER_30						30
#define ACSC_BUFFER_31						31
#define ACSC_BUFFER_32						32
#define ACSC_BUFFER_33						33
#define ACSC_BUFFER_34						34
#define ACSC_BUFFER_35						35
#define ACSC_BUFFER_36						36
#define ACSC_BUFFER_37						37
#define ACSC_BUFFER_38						38
#define ACSC_BUFFER_39						39
#define ACSC_BUFFER_40						40
#define ACSC_BUFFER_41						41
#define ACSC_BUFFER_42						42
#define ACSC_BUFFER_43						43
#define ACSC_BUFFER_44						44
#define ACSC_BUFFER_45						45
#define ACSC_BUFFER_46						46
#define ACSC_BUFFER_47						47
#define ACSC_BUFFER_48						48
#define ACSC_BUFFER_49						49
#define ACSC_BUFFER_50						50
#define ACSC_BUFFER_51						51
#define ACSC_BUFFER_52						52
#define ACSC_BUFFER_53						53
#define ACSC_BUFFER_54						54
#define ACSC_BUFFER_55						55
#define ACSC_BUFFER_56						56
#define ACSC_BUFFER_57						57
#define ACSC_BUFFER_58						58
#define ACSC_BUFFER_59						59
#define ACSC_BUFFER_60						60
#define ACSC_BUFFER_61						61
#define ACSC_BUFFER_62						62
#define ACSC_BUFFER_63						63
#define ACSC_BUFFER_64						64

//////////////////////////////////////////////////////////////////////////////////////////////////
// Servo Processors Definitions
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_SP_ALL							-2
#define ACSC_SP_0							0
#define ACSC_SP_1							1
#define ACSC_SP_2							2
#define ACSC_SP_3							3
#define ACSC_SP_4							4
#define ACSC_SP_5							5
#define ACSC_SP_6							6
#define ACSC_SP_7							7
#define ACSC_SP_8							8
#define ACSC_SP_9							9
#define ACSC_SP_10							10
#define ACSC_SP_11							11
#define ACSC_SP_12							12
#define ACSC_SP_13							13
#define ACSC_SP_14							14
#define ACSC_SP_15							15
#define ACSC_SP_16							16
#define ACSC_SP_17							17
#define ACSC_SP_18							18
#define ACSC_SP_19							19
#define ACSC_SP_20							20
#define ACSC_SP_21							21
#define ACSC_SP_22							22
#define ACSC_SP_23							23
#define ACSC_SP_24							24
#define ACSC_SP_25							25
#define ACSC_SP_26							26
#define ACSC_SP_27							27
#define ACSC_SP_28							28
#define ACSC_SP_29							29
#define ACSC_SP_30							30
#define ACSC_SP_31							31
#define ACSC_SP_32							32
#define ACSC_SP_33							33
#define ACSC_SP_34							34
#define ACSC_SP_35							35
#define ACSC_SP_36							36
#define ACSC_SP_37							37
#define ACSC_SP_38							38
#define ACSC_SP_39							39
#define ACSC_SP_40							40
#define ACSC_SP_41							41
#define ACSC_SP_42							42
#define ACSC_SP_43							43
#define ACSC_SP_44							44
#define ACSC_SP_45							45
#define ACSC_SP_46							46
#define ACSC_SP_47							47
#define ACSC_SP_48							48
#define ACSC_SP_49							49
#define ACSC_SP_50							50
#define ACSC_SP_51							51
#define ACSC_SP_52							52
#define ACSC_SP_53							53
#define ACSC_SP_54							54
#define ACSC_SP_55							55
#define ACSC_SP_56							56
#define ACSC_SP_57							57
#define ACSC_SP_58							58
#define ACSC_SP_59							59
#define ACSC_SP_60							60
#define ACSC_SP_61							61
#define ACSC_SP_62							62
#define ACSC_SP_63							63

//////////////////////////////////////////////////////////////////////////////////////////////////
// PCI interrupts flags
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_INTR_PEG						3
#define ACSC_INTR_MARK1						7
#define ACSC_INTR_MARK2						8
#define ACSC_INTR_EMERGENCY					15
#define ACSC_INTR_PHYSICAL_MOTION_END		16
#define ACSC_INTR_LOGICAL_MOTION_END		17
#define ACSC_INTR_MOTION_FAILURE			18
#define ACSC_INTR_MOTOR_FAILURE				19
#define ACSC_INTR_PROGRAM_END				20
#define ACSC_INTR_COMMAND					21	// FOR BACKWARD COMPATIBILITY
#define ACSC_INTR_ACSPL_PROGRAM_EX			21
#define ACSC_INTR_ACSPL_PROGRAM				22
#define ACSC_INTR_INPUT						23
#define ACSC_INTR_MOTION_START				24
#define ACSC_INTR_MOTION_PHASE_CHANGE		25
#define ACSC_INTR_TRIGGER					26
#define ACSC_INTR_NEWSEGM					27
#define ACSC_INTR_SYSTEM_ERROR				28
#define ACSC_INTR_ETHERCAT_ERROR			29
#define ACSC_INTR_CYCLE						30
#define ACSC_INTR_MESSAGE					31
#define ACSC_INTR_COMM_CHANNEL_CLOSED		32
#define ACSC_INTR_SOFTWARE_ESTOP			33

//////////////////////////////////////////////////////////////////////////////////////////////////
// Bit masks definitions
//////////////////////////////////////////////////////////////////////////////////////////////////

// Communication options
#define ACSC_COMM_USE_CHECKSUM				0x00000001
#define ACSC_COMM_AUTORECOVER_HW_ERROR		0x00000002

// Motion flags
#define ACSC_AMF_WAIT						0x00000001
#define ACSC_AMF_RELATIVE					0x00000002
#define ACSC_AMF_VELOCITY					0x00000004
#define ACSC_AMF_ENDVELOCITY				0x00000008
#define ACSC_AMF_POSITIONLOCK				0x00000010
#define ACSC_AMF_VELOCITYLOCK				0x00000020
#define ACSC_AMF_CYCLIC						0x00000100
#define ACSC_AMF_VARTIME					0x00000200 // SAME AS ACSC_ STALLED
#define ACSC_AMF_STALLED					0x00000200 // SAME AS ACSC_AMF_VARTIME
#define ACSC_AMF_CUBIC						0x00000400
#define ACSC_AMF_EXTRAPOLATED				0x00001000

#define ACSC_AMF_AXISLIMIT					0x00002000 
#define ACSC_AMF_MAXIMUM					0x00004000 // SAME AS ACSC_AMF_SEGTIME

#define ACSC_AMF_SYNCHRONOUS				0x00008000
#define ACSC_AMF_JUNCTIONVELOCITY			0x00010000
#define ACSC_AMF_ANGLE						0x00020000	// SAME AS ACSC_AMF_ACCURATE AND ACSC_AMF_SEGACCEL
#define ACSC_AMF_ACCURATE					0x00020000	// SAME AS ACSC_AMF_ANGLE AND ACSC_AMF_SEGACCEL
#define ACSC_AMF_USERVARIABLES				0x00040000
#define ACSC_AMF_INVERT_OUTPUT				0x00080000
#define ACSC_AMF_CURVEVELOCITY				0x00100000 // SAME AS ACSC_AMF_DWELLTIME

// Corner flags
#define ACSC_AMF_CORNERDEVIATION			0x00200000
#define ACSC_AMF_CORNERRADIUS				0x00400000
#define ACSC_AMF_CORNERLENGTH				0x00800000

//BSEG flags
#define ACSC_AMF_DWELLTIME					0x00100000 // SAME AS ACSC_AMF_CURVEVELOCITY
#define ACSC_AMF_BSEGTIME					0x00004000 // SAME AS ACSC_AMF_MAXIMUM
#define ACSC_AMF_BSEGACC					0x00020000 // SAME AS ACSC_AMF_ANGLE AND ACSC_AMF_ACCURATE
#define ACSC_AMF_BSEGJERK					0x00008000 // SAME AS ACSC_AMF_SYNCHRONOUS

#define ACSC_AMF_CURVEAUTO					0x01000000

// Data collection flags
#define ACSC_DCF_TEMPORAL					0x00000001
#define ACSC_DCF_CYCLIC						0x00000002
#define ACSC_DCF_SYNC					    0x00000004
#define ACSC_DCF_WAIT						0x00000008

// Motor states
#define ACSC_MST_ENABLE						0x00000001
#define ACSC_MST_INPOS						0x00000010			
#define ACSC_MST_MOVE						0x00000020
#define ACSC_MST_ACC						0x00000040

// Motion states
#define ACSC_AST_LEAD						0x00000001
#define ACSC_AST_DC							0x00000002
#define ACSC_AST_PEG						0x00000004
#define ACSC_AST_PEGREADY					0x00000010
#define ACSC_AST_MOVE						0x00000020
#define ACSC_AST_ACC						0x00000040
#define ACSC_AST_SEGMENT					0x00000080
#define ACSC_AST_VELLOCK					0x00000100
#define ACSC_AST_POSLOCK					0x00000200

// Index states
#define ACSC_IST_IND						0x00000001
#define ACSC_IST_IND2						0x00000002
#define ACSC_IST_MARK						0x00000004
#define ACSC_IST_MARK2						0x00000008

// Program states
#define ACSC_PST_COMPILED					0x00000001
#define ACSC_PST_RUN						0x00000002
#define ACSC_PST_SUSPEND					0x00000004
#define ACSC_PST_DEBUG						0x00000020
#define ACSC_PST_AUTO						0x00000080

// Safety control masks
#define ACSC_SAFETY_RL						0x00000001
#define ACSC_SAFETY_LL						0x00000002
#define ACSC_SAFETY_NETWORK					0x00000004
#define ACSC_SAFETY_HOT						0x00000010
#define ACSC_SAFETY_SRL						0x00000020
#define ACSC_SAFETY_SLL						0x00000040
#define ACSC_SAFETY_ENCNC					0x00000080
#define ACSC_SAFETY_ENC2NC					0x00000100
#define ACSC_SAFETY_DRIVE					0x00000200
#define ACSC_SAFETY_ENC						0x00000400
#define ACSC_SAFETY_ENC2					0x00000800
#define ACSC_SAFETY_PE						0x00001000
#define ACSC_SAFETY_CPE						0x00002000
#define ACSC_SAFETY_VL						0x00004000
#define ACSC_SAFETY_AL						0x00008000
#define ACSC_SAFETY_CL						0x00010000
#define ACSC_SAFETY_SP						0x00020000
#define ACSC_SAFETY_STO						0x00040000
#define ACSC_SAFETY_HSSINC					0x00100000

#define ACSC_SAFETY_EXTNT					0x00800000
#define ACSC_SAFETY_TEMP					0x01000000
#define ACSC_SAFETY_PROG					0x02000000
#define ACSC_SAFETY_MEM						0x04000000
#define ACSC_SAFETY_TIME					0x08000000
#define ACSC_SAFETY_ES						0x10000000
#define ACSC_SAFETY_INT						0x20000000
#define ACSC_SAFETY_INTGR					0x40000000
#define ACSC_SAFETY_FAILURE					0x80000000

// EtherCAT flags
#define ACSC_ETHERCAT_1BYTE					0x00000001
#define ACSC_ETHERCAT_2BYTES				0x00000002
#define ACSC_ETHERCAT_4BYTES			    0x00000004
#define ACSC_ETHERCAT_FLOAT					0x00000008


//////////////////////////////////////////////////////////////////////////////////////////////////
// Old Axes Masks
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_MASK_AXIS_X					0x00000001
#define ACSC_MASK_AXIS_Y					0x00000002
#define ACSC_MASK_AXIS_Z					0x00000004
#define ACSC_MASK_AXIS_T					0x00000008
#define ACSC_MASK_AXIS_A					0x00000010
#define ACSC_MASK_AXIS_B					0x00000020
#define ACSC_MASK_AXIS_C					0x00000040
#define ACSC_MASK_AXIS_D					0x00000080

//////////////////////////////////////////////////////////////////////////////////////////////////
// New Axes Masks
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_MASK_AXIS_0					0x0000000000000001
#define ACSC_MASK_AXIS_1					0x0000000000000002
#define ACSC_MASK_AXIS_2					0x0000000000000004
#define ACSC_MASK_AXIS_3					0x0000000000000008
#define ACSC_MASK_AXIS_4					0x0000000000000010
#define ACSC_MASK_AXIS_5					0x0000000000000020
#define ACSC_MASK_AXIS_6					0x0000000000000040
#define ACSC_MASK_AXIS_7					0x0000000000000080
#define ACSC_MASK_AXIS_8					0x0000000000000100
#define ACSC_MASK_AXIS_9					0x0000000000000200
#define ACSC_MASK_AXIS_10					0x0000000000000400
#define ACSC_MASK_AXIS_11					0x0000000000000800
#define ACSC_MASK_AXIS_12					0x0000000000001000
#define ACSC_MASK_AXIS_13					0x0000000000002000
#define ACSC_MASK_AXIS_14					0x0000000000004000
#define ACSC_MASK_AXIS_15					0x0000000000008000
#define ACSC_MASK_AXIS_16					0x0000000000010000
#define ACSC_MASK_AXIS_17					0x0000000000020000
#define ACSC_MASK_AXIS_18					0x0000000000040000
#define ACSC_MASK_AXIS_19					0x0000000000080000
#define ACSC_MASK_AXIS_20					0x0000000000100000
#define ACSC_MASK_AXIS_21					0x0000000000200000
#define ACSC_MASK_AXIS_22					0x0000000000400000
#define ACSC_MASK_AXIS_23					0x0000000000800000
#define ACSC_MASK_AXIS_24					0x0000000001000000
#define ACSC_MASK_AXIS_25					0x0000000002000000
#define ACSC_MASK_AXIS_26					0x0000000004000000
#define ACSC_MASK_AXIS_27					0x0000000008000000
#define ACSC_MASK_AXIS_28					0x0000000010000000
#define ACSC_MASK_AXIS_29					0x0000000020000000
#define ACSC_MASK_AXIS_30					0x0000000040000000
#define ACSC_MASK_AXIS_31					0x0000000080000000
#define ACSC_MASK_AXIS_32					0x0000000100000000
#define ACSC_MASK_AXIS_33					0x0000000200000000
#define ACSC_MASK_AXIS_34					0x0000000400000000
#define ACSC_MASK_AXIS_35					0x0000000800000000
#define ACSC_MASK_AXIS_36					0x0000001000000000
#define ACSC_MASK_AXIS_37					0x0000002000000000
#define ACSC_MASK_AXIS_38					0x0000004000000000
#define ACSC_MASK_AXIS_39					0x0000008000000000
#define ACSC_MASK_AXIS_40					0x0000010000000000
#define ACSC_MASK_AXIS_41					0x0000020000000000
#define ACSC_MASK_AXIS_42					0x0000040000000000
#define ACSC_MASK_AXIS_43					0x0000080000000000
#define ACSC_MASK_AXIS_44					0x0000100000000000
#define ACSC_MASK_AXIS_45					0x0000200000000000
#define ACSC_MASK_AXIS_46					0x0000400000000000
#define ACSC_MASK_AXIS_47					0x0000800000000000
#define ACSC_MASK_AXIS_48					0x0001000000000000
#define ACSC_MASK_AXIS_49					0x0002000000000000
#define ACSC_MASK_AXIS_50					0x0004000000000000
#define ACSC_MASK_AXIS_51					0x0008000000000000
#define ACSC_MASK_AXIS_52					0x0010000000000000
#define ACSC_MASK_AXIS_53					0x0020000000000000
#define ACSC_MASK_AXIS_54					0x0040000000000000
#define ACSC_MASK_AXIS_55					0x0080000000000000
#define ACSC_MASK_AXIS_56					0x0100000000000000
#define ACSC_MASK_AXIS_57					0x0200000000000000
#define ACSC_MASK_AXIS_58					0x0400000000000000
#define ACSC_MASK_AXIS_59					0x0800000000000000
#define ACSC_MASK_AXIS_60					0x1000000000000000
#define ACSC_MASK_AXIS_61					0x2000000000000000
#define ACSC_MASK_AXIS_62					0x4000000000000000
#define ACSC_MASK_AXIS_63					0x8000000000000000

// Buffer masks
#define ACSC_MASK_BUFFER_0					0x0000000000000001
#define ACSC_MASK_BUFFER_1					0x0000000000000002
#define ACSC_MASK_BUFFER_2					0x0000000000000004
#define ACSC_MASK_BUFFER_3					0x0000000000000008
#define ACSC_MASK_BUFFER_4					0x0000000000000010
#define ACSC_MASK_BUFFER_5					0x0000000000000020
#define ACSC_MASK_BUFFER_6					0x0000000000000040
#define ACSC_MASK_BUFFER_7					0x0000000000000080
#define ACSC_MASK_BUFFER_8					0x0000000000000100
#define ACSC_MASK_BUFFER_9					0x0000000000000200
#define ACSC_MASK_BUFFER_10					0x0000000000000400
#define ACSC_MASK_BUFFER_11					0x0000000000000800
#define ACSC_MASK_BUFFER_12					0x0000000000001000
#define ACSC_MASK_BUFFER_13					0x0000000000002000
#define ACSC_MASK_BUFFER_14					0x0000000000004000
#define ACSC_MASK_BUFFER_15					0x0000000000008000
#define ACSC_MASK_BUFFER_16					0x0000000000010000
#define ACSC_MASK_BUFFER_17					0x0000000000020000
#define ACSC_MASK_BUFFER_18					0x0000000000040000
#define ACSC_MASK_BUFFER_19					0x0000000000080000
#define ACSC_MASK_BUFFER_20					0x0000000000100000
#define ACSC_MASK_BUFFER_21					0x0000000000200000
#define ACSC_MASK_BUFFER_22					0x0000000000400000
#define ACSC_MASK_BUFFER_23					0x0000000000800000
#define ACSC_MASK_BUFFER_24					0x0000000001000000
#define ACSC_MASK_BUFFER_25					0x0000000002000000
#define ACSC_MASK_BUFFER_26					0x0000000004000000
#define ACSC_MASK_BUFFER_27					0x0000000008000000
#define ACSC_MASK_BUFFER_28					0x0000000010000000
#define ACSC_MASK_BUFFER_29					0x0000000020000000
#define ACSC_MASK_BUFFER_30					0x0000000040000000
#define ACSC_MASK_BUFFER_31					0x0000000080000000
#define ACSC_MASK_BUFFER_32					0x0000000100000000
#define ACSC_MASK_BUFFER_33					0x0000000200000000
#define ACSC_MASK_BUFFER_34					0x0000000400000000
#define ACSC_MASK_BUFFER_35					0x0000000800000000
#define ACSC_MASK_BUFFER_36					0x0000001000000000
#define ACSC_MASK_BUFFER_37					0x0000002000000000
#define ACSC_MASK_BUFFER_38					0x0000004000000000
#define ACSC_MASK_BUFFER_39					0x0000008000000000
#define ACSC_MASK_BUFFER_40					0x0000010000000000
#define ACSC_MASK_BUFFER_41					0x0000020000000000
#define ACSC_MASK_BUFFER_42					0x0000040000000000
#define ACSC_MASK_BUFFER_43					0x0000080000000000
#define ACSC_MASK_BUFFER_44					0x0000100000000000
#define ACSC_MASK_BUFFER_45					0x0000200000000000
#define ACSC_MASK_BUFFER_46					0x0000400000000000
#define ACSC_MASK_BUFFER_47					0x0000800000000000
#define ACSC_MASK_BUFFER_48					0x0001000000000000
#define ACSC_MASK_BUFFER_49					0x0002000000000000
#define ACSC_MASK_BUFFER_50					0x0004000000000000
#define ACSC_MASK_BUFFER_51					0x0008000000000000
#define ACSC_MASK_BUFFER_52					0x0010000000000000
#define ACSC_MASK_BUFFER_53					0x0020000000000000
#define ACSC_MASK_BUFFER_54					0x0040000000000000
#define ACSC_MASK_BUFFER_55					0x0080000000000000
#define ACSC_MASK_BUFFER_56					0x0100000000000000
#define ACSC_MASK_BUFFER_57					0x0200000000000000
#define ACSC_MASK_BUFFER_58					0x0400000000000000
#define ACSC_MASK_BUFFER_59					0x0800000000000000
#define ACSC_MASK_BUFFER_60					0x1000000000000000
#define ACSC_MASK_BUFFER_61					0x2000000000000000
#define ACSC_MASK_BUFFER_62					0x4000000000000000
#define ACSC_MASK_BUFFER_63					0x8000000000000000

// Input masks
#define ACSC_MASK_INPUT_0					0x00000001
#define ACSC_MASK_INPUT_1					0x00000002
#define ACSC_MASK_INPUT_2					0x00000004
#define ACSC_MASK_INPUT_3					0x00000008
#define ACSC_MASK_INPUT_4					0x00000010
#define ACSC_MASK_INPUT_5					0x00000020
#define ACSC_MASK_INPUT_6					0x00000040
#define ACSC_MASK_INPUT_7					0x00000080
#define ACSC_MASK_INPUT_8					0x00000100
#define ACSC_MASK_INPUT_9					0x00000200
#define ACSC_MASK_INPUT_10					0x00000400
#define ACSC_MASK_INPUT_11					0x00000800
#define ACSC_MASK_INPUT_12					0x00001000
#define ACSC_MASK_INPUT_13					0x00002000
#define ACSC_MASK_INPUT_14					0x00004000
#define ACSC_MASK_INPUT_15					0x00008000
#define ACSC_MASK_INPUT_16					0x00010000
#define ACSC_MASK_INPUT_17					0x00020000
#define ACSC_MASK_INPUT_18					0x00040000
#define ACSC_MASK_INPUT_19					0x00080000
#define ACSC_MASK_INPUT_20					0x00100000
#define ACSC_MASK_INPUT_21					0x00200000
#define ACSC_MASK_INPUT_22					0x00400000
#define ACSC_MASK_INPUT_23					0x00800000
#define ACSC_MASK_INPUT_24					0x01000000
#define ACSC_MASK_INPUT_25					0x02000000
#define ACSC_MASK_INPUT_26					0x04000000
#define ACSC_MASK_INPUT_27					0x08000000
#define ACSC_MASK_INPUT_28					0x10000000
#define ACSC_MASK_INPUT_29					0x20000000
#define ACSC_MASK_INPUT_30					0x40000000
#define ACSC_MASK_INPUT_31					0x80000000

//////////////////////////////////////////////////////////////////////////////////////////////////
// Errors codes
//////////////////////////////////////////////////////////////////////////////////////////////////
#define ACSC_ERRORBASE				100
#define ACSC_UNKNOWNERROR		   	ACSC_ERRORBASE		//Unknown error
#define ACSC_ONLYSYNCHRONOUS    	(ACSC_ERRORBASE+1)	//Asynchronous call is not supported
#define ACSC_ENOENTLOGFILE			(ACSC_ERRORBASE+2)	//No such file or directory
#define ACSC_OLD_FW					(ACSC_ERRORBASE+3)  //FW does not support all desired features
#define ACSC_MEMORY_OVERFLOW		(ACSC_ERRORBASE+4)  //Controllers reply is too long
#define ACSC_EBADFLOGFILE			(ACSC_ERRORBASE+9)	//Invalid log file handle 
#define ACSC_RTOS_NOT_INITIALIZED	(ACSC_ERRORBASE+10) //RTOS is not initialized
#define ACSC_SHM_NOT_INITIALIZED	(ACSC_ERRORBASE+11) //Shared Memory is not initialized
#define ACSC_SHM_WRONG_TYPE			(ACSC_ERRORBASE+12) //Wrong type of shared memory variable
#define ACSC_SHM_INVALID_ADDRESS	(ACSC_ERRORBASE+13) //Invalid address of shared memory variable
#define ACSC_SHE_NOT_SUPPORTED		(ACSC_ERRORBASE+14) //Shared Event is not supported
#define ACSC_SHE_INITERROR			(ACSC_ERRORBASE+15) //Shared Event initialization error
#define ACSC_SHE_NOT_INITIALIZED	(ACSC_ERRORBASE+16) //Shared Event is not initialized
#define ACSC_SHE_ARG_READ_ERROR		(ACSC_ERRORBASE+17) //Shared Event argument read error
#define ACSC_SHE_CLOSE_ERROR		(ACSC_ERRORBASE+18) //Shared Event close error
#define ACSC_EINVALLOGFILE			(ACSC_ERRORBASE+22)	//Write error in Log file
#define ACSC_EMFILELOGFILE			(ACSC_ERRORBASE+24)	//Unable to open file
#define ACSC_ENOSPCLOGFILE			(ACSC_ERRORBASE+28)	//Cannot open Log file. The drive is full
#define ACSC_TIMEOUT				(ACSC_ERRORBASE+30)	//The controller stopped responding
#define ACSC_SIMULATOR_NOT_RUN		(ACSC_ERRORBASE+31)	//Atempted to stop simulator that was not running
#define ACSC_INITFAILURE			(ACSC_ERRORBASE+32)	//Communication initialization failure
#define ACSC_SIMULATOR_RUN_EXT		(ACSC_ERRORBASE+33)	//Stand-alone simulator has been executed not via UMD
#define ACSC_INVALIDHANDLE			(ACSC_ERRORBASE+34)	//Invalid communication handle
#define ACSC_ALLCHANNELSBUSY		(ACSC_ERRORBASE+35)	//All channels are busy
#define ACSC_SIMULATOR_NOT_SET		(ACSC_ERRORBASE+36)	//Stand-alone simulator has not been set in UMD
#define ACSC_RECEIVEDTOOLONG		(ACSC_ERRORBASE+37)	//Received message too long(more than size of user buffer)
#define ACSC_INVALIDBUFSIZE			(ACSC_ERRORBASE+38)	//Functions acsc_DownloadBuffer: the program contains string longer than 2032 bytes
#define ACSC_INVALIDPARAMETERS		(ACSC_ERRORBASE+39) //Function parameters are invalid
#define ACSC_CLOSEDHISTORYBUF		(ACSC_ERRORBASE+40)	//History buffer is closed 
#define ACSC_EMPTYNAMEVAR			(ACSC_ERRORBASE+41)	//Name variable must be specified
#define	ACSC_INPUTPAR				(ACSC_ERRORBASE+42)	//Error in index specification
#define	ACSC_RECEIVEDTOOSMALL		(ACSC_ERRORBASE+43)	//Controller reply contains less values than expected
#define	ACSC_FUNCTIONNOTSUPPORTED	(ACSC_ERRORBASE+45)	//Function is not supported in current version
#define ACSC_INITHISTORYBUFFAILED	(ACSC_ERRORBASE+47) //History buffer initialization failure
#define ACSC_CLOSEDMESSAGEBUF		(ACSC_ERRORBASE+50)	//Unsolicited messages buffer is closed 
#define ACSC_SETCALLBACKERROR		(ACSC_ERRORBASE+51) //Callback registration error
#define ACSC_CALLBACKALREADYSET		(ACSC_ERRORBASE+52) //Callback function has been already installed
#define ACSC_CHECKSUMERROR			(ACSC_ERRORBASE+53)	//Checksum of controller reply error
#define ACSC_REPLIESSEQUENCEERROR	(ACSC_ERRORBASE+54)	//Internal error: Replies sequence error
#define ACSC_WAITFAILED				(ACSC_ERRORBASE+55)	//Internal error: WaitForSingleObject error
#define ACSC_INITMESSAGEBUFFAILED	(ACSC_ERRORBASE+57) //Unsolicited messages buffer initialization failure
#define ACSC_OPERATIONABORTED		(ACSC_ERRORBASE+58) //Non-waiting call has been aborted
#define ACSC_CANCELOPERATIONERROR	(ACSC_ERRORBASE+59) //Error of the non-waiting call cancellation
#define ACSC_COMMANDSQUEUEFULL		(ACSC_ERRORBASE+60)	//Internal error: Queue of transmitted commands is full
#define ACSC_SENDINGFAILED			(ACSC_ERRORBASE+62)	//Internal error: Sending is failed
#define ACSC_RECEIVINGFAILED		(ACSC_ERRORBASE+63)	//Internal error: Receiving is failed
#define ACSC_CHAINSENDINGFAILED		(ACSC_ERRORBASE+64)	//Internal error: Sending of chain is failed
#define ACSC_DUPLICATED_IP			(ACSC_ERRORBASE+65)	//Specified IP address is duplicated
#define ACSC_APPLICATION_NOT_FOUND	(ACSC_ERRORBASE+66) //There is no Application with such Handle
#define ACSC_ARRAY_EXPECTED     	(ACSC_ERRORBASE+67) //Array name was expected
#define ACSC_INVALID_FILE_FORMAT    (ACSC_ERRORBASE+68) //The file is not a valid ANSI data file
#define ACSC_APPSL_CRC				(ACSC_ERRORBASE+71)	// Application Saver Loader CRC Error
#define ACSC_APPSL_HEADERCRC		(ACSC_ERRORBASE+72)	// Application Saver Loader Header CRC Error
#define ACSC_APPSL_FILESIZE		    (ACSC_ERRORBASE+73)	// Application Saver Loader File Size Error
#define ACSC_APPSL_FILEOPEN			(ACSC_ERRORBASE+74)	// Application Saver Loader File Open Error
#define ACSC_APPSL_UNKNOWNFILE		(ACSC_ERRORBASE+75) // Application Saver Loader Unknown File Error
#define ACSC_APPSL_VERERROR         (ACSC_ERRORBASE+76) // Application Saver Loader Format Version Error
#define ACSC_APPSL_SECTION_SIZE		(ACSC_ERRORBASE+77) // Application Saver Loader Section Size is Zero
#define ACSC_TLSERROR				(ACSC_ERRORBASE+79)	//Internal error: Thread local storage error
#define ACSC_INITDRIVERFAILED		(ACSC_ERRORBASE+80)	//PCI driver initialization failure
#define ACSC_CAN_INITFAILURE		(ACSC_ERRORBASE+81)	//CAN library not found or initialization failure
#define ACSC_CLOSED_BY_CONTROLLER	(ACSC_ERRORBASE+82)	//CAN library not found or initialization failure
#define ACSC_INVALIDPOINTER			(ACSC_ERRORBASE+85)	//Pointer to the buffer is invalid || Null pointer recieved instead of user allocated object
#define ACSC_SETPRIORITYERROR		(ACSC_ERRORBASE+89)	//Specified priority for the callback thread cannot be set
#define ACSC_DIRECTDPRAMACCESS		(ACSC_ERRORBASE+90)	//Attempt to access DPRAM not via PCI
#define ACSC_DDERROR				(ACSC_ERRORBASE+91)	//Spii.vxd/sys can not be found or installed
#define ACSC_INVALID_DPRAM_ADDR		(ACSC_ERRORBASE+92) //Invalid DPRAM address 
#define ACSC_OLD_SIMULATOR			(ACSC_ERRORBASE+93) //Old version of SPiiPlus Simulator
#define ACSC_HW_PROBLEM				(ACSC_ERRORBASE+94) //Hardware won't work properly
#define ACSC_FILE_NOT_FOUND			(ACSC_ERRORBASE+95)
#define ACSC_SERVEREXCEPTION		(ACSC_ERRORBASE+97)
#define ACSC_STOPPED_RESPONDING		(ACSC_ERRORBASE+98)
#define ACSC_DLL_UMD_VERSION		(ACSC_ERRORBASE+99) //DLL and Server are not of the same Version


#define ACSC_HW_ERRORBASE			500						// Hardware specific errors
#define ACSC_HW_NO_INT				(ACSC_HW_ERRORBASE+2)
#define ACSC_HW_INT_PERIOD			(ACSC_HW_ERRORBASE+4)
#define ACSC_HW_NO_INT_NOTIF		(ACSC_HW_ERRORBASE+6)
#define ACSC_HW_SPiiFAILURE			(ACSC_HW_ERRORBASE+8)


#define ACSC_CANDEVICE_CUSTOM1		1
#define ACSC_CANDEVICE_CUSTOM2		2
#define ACSC_CANDEVICE_NI			11

#if defined (_ACSC_LIBRARY_DLL_)
#define _ACSCLIB_ __declspec( dllexport )
#else
#define _ACSCLIB_ __declspec( dllimport )
#endif

// Structure is used for non-waiting calls of the library functions
typedef struct 
{
	HANDLE Event;				//signal event
	int	   Ret;					//code of return
} ACSC_WAITBLOCK, *LP_ACSC_WAITBLOCK, WAITBLOCK, *LP_WAITBLOCK;

//Defines for COMLib 6.5
#define ACSC_SYNCHRONOUS		(LP_ACSC_WAITBLOCK)NULL		// Synchronous call
#define ACSC_IGNORE				(LP_ACSC_WAITBLOCK)-1		// Ignore result of Asyncronous call
#define ACSC_ASYNCHRONOUS		(LP_ACSC_WAITBLOCK)-2		// Asynchronous call

typedef enum
{
	Default_Type	= 0,
	String_Type		= 0,
	Buffer_Type		= 1,
	Integer_Type	= 2,
	Real_Type		= 3,
	Scalar_Type		= 4,
	Vector_Type		= 5,
	Matrix_Type		= 6,
	Typeless_Type	= 7,
	Binary_Type		= 8
} ACSC_RETURN_TYPE;

// Structure defines a physical location of PCI card
typedef struct 
{
	unsigned int BusNumber;		//PCI physical bus number of card
	unsigned int SlotNumber;	//PCI physical slot number of card
	unsigned int Function;		//PCI function of card
} ACSC_PCI_SLOT, *LP_ACSC_PCI_SLOT, PCI_SLOT, *LP_PCI_SLOT;

typedef enum 
{
	Minimum,
	Medium,
	Maximum
} ACSC_LOG_DETALIZATION_LEVEL;

typedef enum {
	Compact,
	Formatted,
	Full
} ACSC_LOG_DATA_PRESENTATION;

//This struct describes single UMD connection
typedef struct
{
	char Application[100];				// Application Name
	HANDLE Handle;						// Channel's Handle
	DWORD ProcessId;
} ACSC_CONNECTION_DESC;
typedef enum
{
	ACSC_NOT_CONNECTED = 0,
	ACSC_SERIAL = 1,
	ACSC_PCI = 2,
	ACSC_ETHERNET = 3,
	ACSC_DIRECT = 4
} ACSC_CONNECTION_TYPE;
typedef struct
{
	ACSC_CONNECTION_TYPE Type;
	int SerialPort;
	int SerialBaudRate;
	int PCISlot;
	int EthernetProtocol;
	char EthernetIP[100];
	int EthernetPort;
} ACSC_CONNECTION_INFO;


//This structures used for Application Saver / Loader functions
typedef struct
{
	int length;
	char *string;
} ACSC_APPSL_STRING;

typedef enum
{
	ACSC_ADJ,
	ACSC_SP,
	ACSC_ACSPL,
	ACSC_PAR,
	ACSC_USER,
	ACSC_PROT_STRING
} ACSC_APPSL_FILETYPE;

typedef struct
{
	ACSC_APPSL_FILETYPE type;			// section type
	ACSC_APPSL_STRING filename;			// section file name
	ACSC_APPSL_STRING description;		// section description
	unsigned int size;					// data size
	unsigned int offset;				// offset in the file data section
	unsigned int CRC;					// data CRC
	int inuse;							// selected for save/load
	int error;							// error code
	char *data;							// data as is
} ACSC_APPSL_SECTION;

// Atrriburte key-value pair structure
typedef struct
{
	ACSC_APPSL_STRING key;				// attribute's key (name)
	ACSC_APPSL_STRING value;			// key data
} ACSC_APPSL_ATTRIBUTE;

// Data file structure
// Describe data file header, attributes array and file sections array
typedef struct
{
	ACSC_APPSL_STRING filename;			// file name
	ACSC_APPSL_STRING description;		// file description
	int isNewFile;                      // 1 - if writing new file, 0 - if adding
	int ErrCode;						// Error code from controller
	unsigned int attributes_num;	    // attributes count
	ACSC_APPSL_ATTRIBUTE *attributes;   // attributes array
	unsigned int sections_num;		    // sections count
	ACSC_APPSL_SECTION *sections;	    // sections array
} ACSC_APPSL_INFO;

// Structure of history and message buffer
// Please never change data of this structure!
struct ACSC_HISTORYBUFFER
{
	int    Max;							//buffer size
	int    Cur;							//number of bytes currently stored in the buffer
	int    Ring;						//circular index in the buffer
	char*  Buf;							//pointer to buffer
};

typedef struct ACSC_HISTORYBUFFER *LP_ACSC_HISTORYBUFFER;

typedef int (WINAPI *ACSC_INTR_CALLBACK_FUNC)(int Param);
typedef int (WINAPI *ACSC_INTR_CALLBACK_FUNC_EXT)(int Param, void* CardContext);
typedef int (WINAPI *ACSC_USER_CONDITION_FUNC)(HANDLE Handle);
#define ACSC_DUMMY_CALLBACK (ACSC_INTR_CALLBACK_FUNC)-1
#define ACSC_DUMMY_CALLBACK_EXT (ACSC_INTR_CALLBACK_FUNC_EXT)-1

//////////////////////////////////////////////////////////////////////////////////////////////////
typedef int (WINAPI *ACSC_USER_CALLBACK_FUNCTION)(unsigned __int64 Param, void* CardContext);
#define ACSC_DUMMY_CALLBACK_FUNCTION (ACSC_USER_CALLBACK_FUNCTION)-1
//////////////////////////////////////////////////////////////////////////////////////////////////


#ifdef __cplusplus
extern "C" {
#endif


//////////////////////////////////////////////////////////////////////////////////////////////////
// If you want to load ACSC.dll dynamically at runtime, 
// define ACSC_RUNTIME_DYNAMIC_LINKING in your project before including this file
// Otherwise load-time dynamic linking is implied
//////////////////////////////////////////////////////////////////////////////////////////////////
#if !defined (ACSC_RUNTIME_DYNAMIC_LINKING)
//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates communication via serial port
//////////////////////////////////////////////////////////////////////////////////////////////////
HANDLE _ACSCLIB_ WINAPI acsc_OpenCommSerial(int Channel, int Rate);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates communication via Ethernet
//////////////////////////////////////////////////////////////////////////////////////////////////
HANDLE _ACSCLIB_ WINAPI acsc_OpenCommEthernet(char* Address, int Port);

// new functions with any custom port as parameter
HANDLE _ACSCLIB_ WINAPI acsc_OpenCommEthernetTCP(char* Address, int Port);
HANDLE _ACSCLIB_ WINAPI acsc_OpenCommEthernetUDP(char* Address, int Port);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates direct communication with simulator
//////////////////////////////////////////////////////////////////////////////////////////////////
HANDLE _ACSCLIB_ WINAPI acsc_OpenCommDirect();


//////////////////////////////////////////////////////////////////////////////////////////////////
// The functions collects IP addresses of SPiiPlus cards connected to the local segment
/////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ acsc_GetEthernetCards(struct in_addr *IPaddresses,int Max, int *Ncontrollers,unsigned long BroadcastAddress);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates communication via PCI device driver
//////////////////////////////////////////////////////////////////////////////////////////////////
HANDLE _ACSCLIB_ WINAPI acsc_OpenCommPCI(int SlotNumber);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a PCI bus information for the PCI cards installed
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetPCICards(ACSC_PCI_SLOT* Cards, int Count, int* ObtainedCards);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function closes communication (for all kinds of communications)
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CloseComm(HANDLE Handle);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sends message
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Send(HANDLE Handle, char* Buf, int Count, ACSC_WAITBLOCK* Wait);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function receives message
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Receive(HANDLE Handle, char* Buf, int Count, int* Received, ACSC_WAITBLOCK* Wait);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function provides transaction: sends request and receives reply
//////////////////////////////////////////////////////////////////////////////////////////////////
int	_ACSCLIB_ WINAPI acsc_Transaction(HANDLE Handle, char* OutBuf, int OutCount, char* InBuf, int InCount, int* Received, ACSC_WAITBLOCK* Wait);



//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sends a command to the controller and analyzes the controller response.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Command(HANDLE Handle, char* OutBuf, int OutCount, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for completion of asynchronous call and retrieves a data.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitForAsyncCall(HANDLE Handle, void* Buf, int* Received, ACSC_WAITBLOCK* Wait, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function cancels any asynchronous (non-waiting) call
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CancelOperation(HANDLE Handle, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the last error code
//////////////////////////////////////////////////////////////////////////////////////////////////
// function of the new library
int	_ACSCLIB_ WINAPI acsc_GetLastError();


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the explanation of an error code. 
//////////////////////////////////////////////////////////////////////////////////////////////////
int	_ACSCLIB_ WINAPI acsc_GetErrorString(HANDLE Handle, int ErrorCode, char* ErrorStr, int Count, int* Received);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets communication call delay
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetQueueOverflowTimeout(HANDLE Handle, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves communication call delay 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetQueueOverflowTimeout(HANDLE Handle);
//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets communication timeout
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetTimeout(HANDLE Handle, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves communication timeout
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetTimeout(HANDLE Handle);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves default communication timeout
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetDefaultTimeout(HANDLE Handle);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the number of iterations of one transaction
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetIterations(HANDLE Handle, int Iterations);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets communication options
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetCommOptions(HANDLE Handle, unsigned int Options);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves communication options
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetCommOptions(HANDLE Handle, unsigned int* Options);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves ACSC Library version
//////////////////////////////////////////////////////////////////////////////////////////////////
unsigned int _ACSCLIB_ WINAPI acsc_GetLibraryVersion();

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function loads ACSPL+ program to the specified program buffer.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_LoadBuffer(HANDLE Handle, int Buffer, char* Text, int Count, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function loads ACSPL+ program to the specified program buffer.
// Service lines are ignored.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_LoadBufferIgnoreServiceLines(HANDLE Handle, int Buffer, char* Text, int Count, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function loads ACSPL+ programs to the specified program buffers.
// From *.prg file
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_LoadBuffersFromFile(HANDLE Handle,  char* Filename, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function appends one or more ACSPL+ lines to the program in the specified program buffer.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AppendBuffer(HANDLE Handle, int Buffer, char* Text, int Count, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function downloads text to a program buffer. The function is similar to the function acsc_AppendBuffer() 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DownloadBuffer(HANDLE Handle, int Buffer, char* Text, int Count, ACSC_WAITBLOCK* Wait);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function uploads text from a program buffer 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_UploadBuffer(HANDLE Handle, int Buffer, int Offset, char* Text, int Count, int* Received, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function deletes the specified ACSPL+ program lines in the specified program buffer.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ClearBuffer(HANDLE Handle, int Buffer, int FromLine, int ToLine, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function compiles ACSPL+ program in the specified program buffer(s).
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CompileBuffer(HANDLE Handle, int Buffer, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function starts up ACSPL+ program in the specified program buffer.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_RunBuffer(HANDLE Handle, int Buffer, char* Label, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function stops ACSPL+ program in the specified program buffer(s).
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_StopBuffer(HANDLE Handle, int Buffer, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function suspends ACSPL+ program in the specified program buffer(s).
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SuspendBuffer(HANDLE Handle, int Buffer, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads value(s) from integer variable
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ReadInteger(HANDLE Handle, int NBuf, char* Var, int From1, int To1, int From2, int To2, int* Values, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function writes value(s) to integer variable
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WriteInteger(HANDLE Handle, int NBuf, char* Var, int From1, int To1, int From2, int To2, int* Values, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads value(s) from real variable
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ReadReal(HANDLE Handle, int NBuf, char* Var, int From1, int To1, int From2, int To2, double* Values, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function writes value(s) to real variable
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WriteReal(HANDLE Handle, int NBuf, char* Var, int From1, int To1, int From2, int To2, double* Values, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function captures communication
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CaptureComm(HANDLE Handle);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function releases communication
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ReleaseComm(HANDLE Handle);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates history buffer
//////////////////////////////////////////////////////////////////////////////////////////////////
LP_ACSC_HISTORYBUFFER _ACSCLIB_ WINAPI acsc_OpenHistoryBuffer(HANDLE Handle, int Size);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function closes history buffer
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CloseHistoryBuffer(HANDLE Handle);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the contents of the history buffer
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetHistory(HANDLE Handle, char* Buf, int Count, int* Received, BOOL bClear);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates unsolicited messages buffer
//////////////////////////////////////////////////////////////////////////////////////////////////
LP_ACSC_HISTORYBUFFER _ACSCLIB_ WINAPI acsc_OpenMessageBuffer(HANDLE Handle, int Size);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function closes unsolicited messages buffer
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CloseMessageBuffer(HANDLE Handle);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves all stored unsolicited messages from buffer
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetMessage(HANDLE Handle, char* Buf, int Count, int* Received, BOOL bClear);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a single unsolicited message or exits by timeout
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetSingleMessage(HANDLE Handle, char* Buf, int Count, int* Received, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function opens logfile. Now all communication will be saved in the logfile.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_OpenLogFile(HANDLE Handle, char* FileName);
int _ACSCLIB_ WINAPI acsc_OpenSCLogFile(HANDLE Handle, char* FileName);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function closes logfile. 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CloseLogFile(HANDLE Handle);
int _ACSCLIB_ WINAPI acsc_CloseSCLogFile(HANDLE Handle);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function writes to logfile. 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WriteLogFile(HANDLE Handle, char* Buf, int Count);
int _ACSCLIB_ WINAPI acsc_WriteSCLogFile(HANDLE Handle, char* Buf, int Count);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function writes to logfile. 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_FlushLogFile(char* Filename);
int _ACSCLIB_ WINAPI acsc_FlushSCLogFile(char* Filename, BOOL bClear);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the data of firmware log
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetLogData(HANDLE Handle, char* Buf, int Count, int* Received, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function defines a value of motion velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetVelocity(HANDLE Handle, int Axis, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a value of motion velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetVelocity(HANDLE Handle, int Axis, double* Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function defines a value of motion acceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetAcceleration(HANDLE Handle, int Axis, double Acceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a value of motion acceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetAcceleration(HANDLE Handle, int Axis, double* Acceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function defines a value of motion deceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetDeceleration(HANDLE Handle, int Axis, double Deceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a value of motion deceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetDeceleration(HANDLE Handle, int Axis, double* Deceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function defines a value of motion jerk.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetJerk(HANDLE Handle, int Axis, double Jerk, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a value of motion jerk.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetJerk(HANDLE Handle, int Axis, double* Jerk, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function defines a value of kill deceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetKillDeceleration(HANDLE Handle, int Axis, double KillDeceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a value of kill deceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetKillDeceleration(HANDLE Handle, int Axis, double* KillDeceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function provides on-the-fly change a value of motion velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetVelocityImm(HANDLE Handle, int Axis, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function provides on-the-fly change a value of motion acceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetAccelerationImm(HANDLE Handle, int Axis, double Acceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function provides on-the-fly change a value of motion deceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetDecelerationImm(HANDLE Handle, int Axis, double Deceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function provides on-the-fly change a value of motion jerk.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetJerkImm(HANDLE Handle, int Axis, double Jerk, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function provides on-the-fly change a value of kill deceleration.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetKillDecelerationImm(HANDLE Handle, int Axis, double KillDeceleration, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function assigns a current value of target position for several axes.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetTargetPositionM(HANDLE Handle, int* Axes, double *TargetPositions, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function assigns a current value of target position.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetTargetPosition(HANDLE Handle, int Axis, double TargetPosition, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a current value of motor feedback position.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetTargetPosition(HANDLE Handle, int Axis, double* TargetPosition, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function assigns a current value of target position.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetFPosition(HANDLE Handle, int Axis, double FPosition, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a current value of motor feedback position.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetFPosition(HANDLE Handle, int Axis, double* FPosition, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function assigns a current value of reference position.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetRPosition(HANDLE Handle, int Axis, double RPosition, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a current value of reference position.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetRPosition(HANDLE Handle, int Axis, double* RPosition, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a current value of motor feedback velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetFVelocity(HANDLE Handle, int Axis, double* FVelocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves a current value of reference velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetRVelocity(HANDLE Handle, int Axis, double* RVelocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function activates a motor.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Enable(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function activates several motors.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_EnableM(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function shuts off a motor.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Disable(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function shuts off several motors.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DisableM(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function shuts off all motors.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DisableAll(HANDLE Handle, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function performs commutation to brushless motor.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Commut(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function performs commutation to brushless motor. Extended parameters
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CommutExt(HANDLE Handle, int Axis,float Current,int Settle,int Slope, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function creates a coordinate system for multi-axis motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Group(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_ff(void **ptr);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function breaks down an axis group created before by the acsc_Group function.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Split(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function breaks down all axis groups created before by the acsc_Group function.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SplitAll(HANDLE Handle, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function starts up a motion that is waiting in the specified motion queue.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Go(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function synchronously starts up several motions 
// that are waiting in the specified motion queues. 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GoM(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates a motion using the full deceleration profile.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Halt(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates several motions using the full deceleration profile.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_HaltM(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates a motion using reduced deceleration profile.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Kill(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates several motions using reduced deceleration profile.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_KillM(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates all currently executed motions.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_KillAll(HANDLE Handle, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates a motion immediately and 
// provides a smooth transition to the next motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Break(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates several motions immediately and 
// provides a smooth transition to the next motions.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_BreakM(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a single-axis motion to the specified point.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ToPoint(HANDLE Handle, int Flags, int Axis, double Point, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis motion to the specified point
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ToPointM(HANDLE Handle, int Flags, int* Axes, double* Point, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a single-axis motion to the specified point 
// using the specified velocity or end velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtToPoint(HANDLE Handle, int Flags, int Axis, double Point, double Velocity, double EndVelocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis motion to the specified point 
// using the specified velocity or end velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtToPointM(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a single-axis track motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Track(HANDLE Handle, int Flags, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multile-axis track motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_TrackM(HANDLE Handle, int Flags, int *Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function clears the current faults and results of previous faults stored in the MERR variable.
// For single axis
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_FaultClear(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function clears the current faults and results of previous faults stored in the MERR variable.
// For multiple axes
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_FaultClearM(HANDLE Handle, int *Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads number of available axes
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetAxesCount(HANDLE Handle, double *Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads number of available ACSPL+ programming buffers
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetBuffersCount(HANDLE Handle, double *Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads index of D-Buffer
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetDBufferIndex(HANDLE Handle, double *Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads system information
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SysInfo(HANDLE Handle, int Key, double *Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function writes system configuration
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetConf(HANDLE Handle, int Key, int Index, double Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads system configuration
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetConf(HANDLE Handle, int Key, int Index, double *Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function writes system configuration-obsolete
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Setconf(HANDLE Handle, int Key, int Index, int Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function reads system configuration-obsolete
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Getconf(HANDLE Handle, int Key, int Index, int *Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a single-axis jog motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Jog(HANDLE Handle, int Flags, int Axis, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis jog motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_JogM(HANDLE Handle, int Flags, int* Axes, int* Direction, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates calculating of master value for an axis.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetMaster(HANDLE Handle, int Axis, char* Formula, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a master-slave motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Slave(HANDLE Handle, int Flags, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a master-slave motion with a limited following area.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SlaveStalled(HANDLE Handle, int Flags, int Axis, double Left, double Right, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a single-axis multi-point motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_MultiPoint(HANDLE Handle, int Flags, int Axis, double Dwell, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis multi-point motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_MultiPointM(HANDLE Handle, int Flags, int* Axes, double Dwell, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a single-axis spline motion. 
// The motion follows an arbitrary path defined by a set of points.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Spline(HANDLE Handle, int Flags, int Axis, double Period, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis spline motion. 
// The motion follows an arbitrary path defined by a set of points.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SplineM(HANDLE Handle, int Flags, int* Axes, double Period, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Segment(HANDLE Handle, int Flags, int* Axes, double* Point, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SegmentedMotion(HANDLE Handle, int Flags, int* Axes, double* Point, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis extended segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtendedSegmentedMotion(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, double JunctionVelocity, double Angle, double StarvationMargin, char* Segments, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis extended segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtendedSegmentedMotionExt(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, double JunctionVelocity, double Angle, 
	double CurveVelocity, double Deviation, double Radius, double MaxLength, double StarvationMargin, char* Segments, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates a multi-axis blended segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_BlendedSegmentMotion(HANDLE Handle, int Flags, int* Axes, double* Point, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK *Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a linear segment to a blended segmented motion
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_BlendedLine(HANDLE Handle, int Flags, int* Axes,double* Point, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, coordinates of the final point and the direction of rotation.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_BlendedArc1(HANDLE Handle, int Flags, int* Axes, double* Center, double* FinalPoint, int Rotation, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, rotation angle
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_BlendedArc2 (HANDLE Handle, int Flags, int* Axes, double* Center, double Angle, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK* Wait);


//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a linear segment to a segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Line(HANDLE Handle, int* Axes, double* Point, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a linear segment to a segmented motion and specifies a motion velocity.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtLine(HANDLE Handle, int* Axes, double* Point, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a linear segment to a segmented motion
// Specifies motion velocity, end motion velocity, and user variables parameters
// -- Obsolete --
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SegmentLine(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a linear segment to a segmented motion
// Specifies motion velocity, end motion velocity, and user variables parameters
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SegmentLineExt(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, double Time, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, coordinates of the final point and the direction of rotation.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Arc1(HANDLE Handle, int* Axes, double* Center, double* FinalPoint, int Rotation, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, coordinates of the final point, direction of rotation and 
// the vector velocity for the current segment.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtArc1(HANDLE Handle, int* Axes, double* Center, double* FinalPoint, int Rotation, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, coordinates of the final point, direction of rotation, vector velocity,
// end motion velocity, and user variables parameters for the current segment.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SegmentArc1(HANDLE Handle, int Flags, int* Axes, double* Center, double* FinalPoint, int Rotation, double Velocity, double EndVelocity, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, coordinates of the final point, direction of rotation, vector velocity,
// end motion velocity, and user variables parameters for the current segment.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SegmentArc1Ext(HANDLE Handle, int Flags, int* Axes, double* Center, double* FinalPoint, int Rotation, double Velocity, double EndVelocity, double Time, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point and rotation angle.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Arc2(HANDLE Handle, int* Axes, double* Center, double Angle, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, rotation angle and the vector velocity for the current segment.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtArc2(HANDLE Handle, int* Axes, double* Center, double Angle, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, rotation angle, vector velocity,
// end motion velocity, and user variables parameters for the current segment.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SegmentArc2(HANDLE Handle, int Flags, int* Axes, double* Center, double Angle, double Velocity, double EndVelocity, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an arc segment to a segmented motion and specifies the coordinates 
// of center point, rotation angle, vector velocity,
// end motion velocity, and user variables parameters for the current segment.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SegmentArc2Ext(HANDLE Handle, int Flags, int* Axes, double* Center, double Angle, double Velocity, double EndVelocity, double Time, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function provides a smooth transition between two segments of segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Stopper(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets a projection matrix for segmented motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Projection(HANDLE Handle, int* Axes, char* Matrix, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a single-axis multi-point or spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddPoint(HANDLE Handle, int Axis, double Point, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a multi-axis multi-point or spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddPointM(HANDLE Handle, int* Axes, double* Point, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a single-axis multi-point or spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtAddPoint(HANDLE Handle, int Axis, double Point, double Rate, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a multi-axis multi-point or spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ExtAddPointM(HANDLE Handle, int* Axes, double* Point, double Rate, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a single-axis PVT spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddPVTPoint(HANDLE Handle, int Axis, double Point, double Velocity,double TimeInterval, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a multi-axis PVT spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddPVTPointM(HANDLE Handle, int *Axis, double *Point, double *Velocity,double TimeInterval, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a single-axis PV spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddPVPoint(HANDLE Handle, int Axis, double Point, double Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds a point to a multi-axis PV spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddPVPointM(HANDLE Handle, int *Axis, double *Point, double *Velocity, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an array of points to a single-axis multi-point or spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddMPoint(HANDLE Handle, int Axis, char* Name, int Count, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function adds an array of points to a multi-axis multi-point or spline motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AddMPointM(HANDLE Handle, int* Axes, char* Name, int Count, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function informs the controller, that no more points will be specified for the current single-axis motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_EndSequence(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function informs the controller, that no more points or segments will be specified for the current multi-axis motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_EndSequenceM(HANDLE Handle, int* Axes, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates data collection.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_Collect(HANDLE Handle, int Flags, char* Array, int NSample, int Period, char** Vars, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates data collection.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CollectB(HANDLE Handle, int Flags, char* Array, int NSample, int Period, char* Vars, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates data collection.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DataCollection(HANDLE Handle, int Flags, int Axis, char* Array, int NSample, int Period, char* Vars, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function initiates data collection.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DataCollectionExt(HANDLE Handle, int Flags, int Axis, char* Array, int NSample, double Period, char* Vars, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates data collection.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_StopCollect(HANDLE Handle, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current motor state.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetMotorState(HANDLE Handle, int Axis, int* State, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current axis state.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetAxisState(HANDLE Handle, int Axis, int* State, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the index and mark variables.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetIndexState(HANDLE Handle, int Axis, int* State, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function resets the specified bits of the index/mark state.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ResetIndexState(HANDLE Handle, int Axis, int Mask, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the program buffer.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetProgramState(HANDLE Handle, int Buffer, int* State, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified digital input.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetInput(HANDLE Handle, int Port, int Bit, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified digital input port.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetInputPort(HANDLE Handle, int Port, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified digital output.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetOutput(HANDLE Handle, int Port, int Bit, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified digital output port.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetOutputPort(HANDLE Handle, int Port, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the specified digital output to the specified value.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetOutput(HANDLE Handle, int Port, int Bit, int Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the specified digital output port to the specified value.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetOutputPort(HANDLE Handle, int Port, int Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current numerical value of the specified analog inputs.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetAnalogInput(HANDLE Handle, int Port, int* Value, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetAnalogInputNT(HANDLE Handle, int Port, double* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current numerical value of  the specified analog outputs.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetAnalogOutput(HANDLE Handle, int Port, int* Value, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetAnalogOutputNT(HANDLE Handle, int Port, double* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function writes the current numerical value to the specified analog outputs.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetAnalogOutput(HANDLE Handle, int Port, int Value, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_SetAnalogOutputNT(HANDLE Handle, int Port, double Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified extended input.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetExtInput(HANDLE Handle, int Port, int Bit, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified extended input port.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetExtInputPort(HANDLE Handle, int Port, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified extended output.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetExtOutput(HANDLE Handle, int Port, int Bit, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified extended output port.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetExtOutputPort(HANDLE Handle, int Port, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the specified extended output to the specified value.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetExtOutput(HANDLE Handle, int Port, int Bit, int Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the specified extended output port to the specified value.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetExtOutputPort(HANDLE Handle, int Port, int Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the set of bits, that indicate the motor or system faults.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetFault(HANDLE Handle, int Axis, int* Fault, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the mask, that defines which controller faults are examined and processed.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetFaultMask(HANDLE Handle, int Axis, int* Mask, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the mask, that enables/disables the examination and processing of the controller faults.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetFaultMask(HANDLE Handle, int Axis, int Mask, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function enables the specified motor or system fault.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_EnableFault(HANDLE Handle, int Axis, int Fault, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function disables the specified motor or system fault.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DisableFault(HANDLE Handle, int Axis, int Fault, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the mask, that defines for which motor or system faults the controller provides default response.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetResponseMask(HANDLE Handle, int Axis, int* Mask, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the mask, that defines for which motor or system faults the controller provides default response.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetResponseMask(HANDLE Handle, int Axis, int Mask, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function enables the response to the specified motor or system fault.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_EnableResponse(HANDLE Handle, int Axis, int Response, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function disables the default response to the specified motor or system fault.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DisableResponse(HANDLE Handle, int Axis, int Response, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified safety input.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetSafetyInput(HANDLE Handle, int Axis, int Input, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the current state of  the specified safety input port.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetSafetyInputPort(HANDLE Handle, int Axis, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the set of bits that define inversion for the specified safety input port.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetSafetyInputPortInv(HANDLE Handle, int Axis, int* Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the set of bits that define inversion for the specified safety input port.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetSafetyInputPortInv(HANDLE Handle, int Axis, int Value, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the end of a motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitMotionEnd(HANDLE Handle, int Axis, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the logical end of a motion.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitLogicalMotionEnd(HANDLE Handle, int Axis, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the end of data collection.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitCollectEnd(HANDLE Handle, int Timeout); //Deprecated

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the end of data collection.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitCollectEndExt(HANDLE Handle, int Timeout, int Axis);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the program termination in the specified buffer.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitProgramEnd(HANDLE Handle, int Buffer, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the specified state of the specified motor.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitMotorEnabled(HANDLE Handle, int Axis, int State, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the specified state of the specified motor.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitMotorCommutated(HANDLE Handle, int Axis, int State, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the specified state of digital input.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitInput(HANDLE Handle, int Port, int Bit, int State, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for user-defined condition.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitUserCondition(HANDLE Handle, ACSC_USER_CONDITION_FUNC UserCondition, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function waits for the readiness of the PEG engine.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_WaitPegReadyNT(HANDLE Handle, int Axis, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function installs a user-defined callback function for the specified interrupt condition
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetCallback(HANDLE Handle, ACSC_INTR_CALLBACK_FUNC Callback, int Interrupt);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function installs a user-defined callback function for the specified interrupt condition
// with specified card context
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetCallbackExt(HANDLE Handle, ACSC_INTR_CALLBACK_FUNC_EXT Callback,void* CardContext, int Interrupt);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function installs a user-defined callback function for the specified interrupt condition
// with specified card context
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_InstallCallback(HANDLE Handle, ACSC_USER_CALLBACK_FUNCTION Callback,void* CardContext, int Interrupt);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the priority for all callback threads. 
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetCallbackPriority(HANDLE Handle, int Priority);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the mask for specified interrupt
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetInterruptMask(HANDLE Handle, int Interrupt, unsigned int Mask);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function sets the mask for specified callback
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetCallbackMask(HANDLE Handle, int Interrupt, unsigned __int64 Mask);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the mask for specified interrupt
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetInterruptMask(HANDLE Handle, int Interrupt, unsigned int* Mask);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the mask for specified callback
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetCallbackMask(HANDLE Handle, int Interrupt, unsigned __int64* Mask);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function creates the persistent global variable.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DeclareVariable(HANDLE Handle, int Type, char* Name, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function deletes all persistent global variables.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ClearVariables(HANDLE Handle, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the firmware version of the controller.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetFirmwareVersion(HANDLE Handle, char* Version, int Count, int* Received, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the controller serial number.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetSerialNumber(HANDLE Handle, char* SerialNumber, int Count, int* Received, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function terminates a motion using reduced deceleration profile with Reason of kill.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_KillExt(HANDLE Handle, int Axis,int Reason, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function disables motor and sets Reason of disable.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DisableExt(HANDLE Handle, int Axis,int Reason, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the reason why the motor was disabled.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetMotorError(HANDLE Handle, int Axis, int* Error, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the termination code of the last executed motion of the specified axis.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetMotionError(HANDLE Handle, int Axis, int* Error, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the error code of the last program error encountered in the specified buffer.
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetProgramError(HANDLE Handle, int Buffer, int* Error, ACSC_WAITBLOCK* Wait);

////////////////////////////////////////////////////////////////////////////////////////////////
// Those functions access directly DPRAM via PCI bus only
////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ReadDPRAMInteger(HANDLE Handle, int index, int* result);
int _ACSCLIB_ WINAPI acsc_WriteDPRAMInteger(HANDLE Handle, int index, int data);
int _ACSCLIB_ WINAPI acsc_ReadDPRAMReal(HANDLE Handle, int index, double* result);
int _ACSCLIB_ WINAPI acsc_WriteDPRAMReal(HANDLE Handle, int index, double data);

////////////////////////////////////////////////////////////////////////////////////////////////
// Those functions provides access to Shared Memory variables
////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetSharedMemoryAddress(HANDLE Handle, int NBuf, char* Var, unsigned int* Address, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_ReadSharedMemoryReal(HANDLE Handle, unsigned int Address, int From1, int To1, int From2, int To2, double* Values);
int _ACSCLIB_ WINAPI acsc_ReadSharedMemoryInteger(HANDLE Handle, unsigned int Address, int From1, int To1, int From2, int To2, int* Values);
int _ACSCLIB_ WINAPI acsc_WriteSharedMemoryReal(HANDLE Handle, unsigned int Address, int From1, int To1, int From2, int To2, double* Values);
int _ACSCLIB_ WINAPI acsc_WriteSharedMemoryInteger(HANDLE Handle, unsigned int Address, int From1, int To1, int From2, int To2, int* Values);

/////////////////////////////////////////////////////////////////////////////////////////////////////
//This function defines communication server IP address
/////////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetServer(char *IP);

/////////////////////////////////////////////////////////////////////////////////////////////////////
//This function defines communication server IP address and Port
/////////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_SetServerExt(char *IP,int Port);
int _ACSCLIB_ WINAPI acsc_SetServerExtLogin(char *IP, int Port, char *Username, char *Password, char *Domain);

/////////////////////////////////////////////////////////////////////////////////////////////////////
// These functions are related to Position Event Generation (PEG)
/////////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_PegI(HANDLE Handle, int Flags, int Axis, double Width, int FirstPoint, int Interval, int LastPoint, int TbNumber,double TbPeriod, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_PegR(HANDLE Handle, int Flags, int Axis, double Width, char* PointArray, char* StateArray, int TbNumber, double TbPeriod, ACSC_WAITBLOCK* Wait);

int _ACSCLIB_ WINAPI acsc_PegInc(HANDLE Handle, int Flags,int Axis, double Width, double FirstPoint, double Interval, double LastPoint, int TbNumber, double TbPeriod, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_PegRandom(HANDLE Handle, int Flags,int Axis, double Width, char* PointArray, char* StateArray, int TbNumber, double TbPeriod, ACSC_WAITBLOCK* Wait);

int _ACSCLIB_ WINAPI acsc_AssignPins(HANDLE Handle, int Axis, unsigned short Mask, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_StopPeg(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

int _ACSCLIB_ WINAPI acsc_AssignPegNT(HANDLE Handle, int Axis, int EngToEncBitCode, int GpOutsBitCode, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_AssignPegOutputsNT(HANDLE Handle, int Axis, int OutputIndex, int BitCode, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_AssignFastInputsNT(HANDLE Handle, int Axis, int InputIndex, int BitCode, ACSC_WAITBLOCK* Wait);

int _ACSCLIB_ WINAPI acsc_PegIncNT(HANDLE Handle, int Flags, int Axis, double Width, double FirstPoint, double Interval, double LastPoint, int TbNumber, double TbPeriod, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_PegRandomNT(HANDLE Handle, int Flags, int Axis, double Width, int Mode, int FirstIndex, int LastIndex, char* PointArray, char* StateArray, int TbNumber, double TbPeriod, ACSC_WAITBLOCK* Wait);

int _ACSCLIB_ WINAPI acsc_StartPegNT(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_StopPegNT(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

/////////////////////////////////////////////////////////////////////////////////////////////////////
//These functions are used for reading data from text files
/////////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_LoadFileToIntegerVariable(HANDLE Handle, int NBuf, char *Var, int From1, int To1, int From2, int To2, char* Filename, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_LoadFileToRealVariable(HANDLE Handle, int NBuf, char *Var, int From1, int To1, int From2, int To2, char* Filename, ACSC_WAITBLOCK* Wait);

int _ACSCLIB_ WINAPI acsc_DownloadBinVariableToFile(HANDLE Handle, int NBuf, char *Var, int Size, int From1, int To1, int From2, int To2, char* Filename, char* Format, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_SetLogFileOptions(HANDLE Handle,ACSC_LOG_DETALIZATION_LEVEL Detalization, ACSC_LOG_DATA_PRESENTATION Presentation);

int _ACSCLIB_ WINAPI acsc_LoadDataToController(HANDLE Handle,int Dest, char* DestName, int From1, int To1, int From2, int To2, char* SrcFileName, int SrcNumFormat, BOOL bTranspose,   ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_UploadDataFromController(HANDLE Handle, int Src, char *SrcName, int SrcNumFormat, int From1, int To1, int From2, int To2, char* DestFileName, char* DestNumFormat, BOOL bTranspose, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function copies file to controller
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CopyFileToController(HANDLE Handle, char* SourceFileName, char* DestinationFileName, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function deletes file from controller
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_DeleteFileFromController(HANDLE Handle, char* FileName, ACSC_WAITBLOCK* Wait);

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves the list of all currently opened communication channels(connections), on active Server.//
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetConnectionsList(ACSC_CONNECTION_DESC* ConnectionsList, int MaxNumConnections, int* NumConnections);

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// The function retrieves additional information of specified connection, on active Server.						 //
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetConnectionInfo(HANDLE Handle, ACSC_CONNECTION_INFO* ConnectionInfo);

////////////////////////////////////////////////////////////////////////////////////////
// The function terminates single communication channel(connection), on active Server.//
////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_TerminateConnection(ACSC_CONNECTION_DESC* Connection);

////////////////////////////////////////////////////////////////////////////////////////
// The functions for managing new UMD EmergencyStop functionality                     //
////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_RegisterEmergencyStop();
int _ACSCLIB_ WINAPI acsc_UnregisterEmergencyStop();

////////////////////////////////////////////////////////////////////////////////////////
// The function returns version of UMD                                                //
////////////////////////////////////////////////////////////////////////////////////////
unsigned int _ACSCLIB_ WINAPI acsc_GetUMDVersion();

////////////////////////////////////////////////////////////////////////////////////////
// These functions for Application Saver Loader functionality                         //
////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_AnalyzeApplication(HANDLE Handle, const char * FileName, ACSC_APPSL_INFO** Info, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_FreeApplication(ACSC_APPSL_INFO* Info);
int _ACSCLIB_ WINAPI acsc_SaveApplication(HANDLE Handle, const char * FileName, ACSC_APPSL_INFO* Info, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_LoadApplication(HANDLE Handle, const char * FileName, ACSC_APPSL_INFO* Info, ACSC_WAITBLOCK* Wait);

//////////////////////////////////////////////////////////////////////////////////////////////////
// These functions reboot controler with or without restoring defaults
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ControllerReboot(HANDLE Handle, int Timeout);
int _ACSCLIB_ WINAPI acsc_ControllerFactoryDefault(HANDLE Handle, int Timeout);

//////////////////////////////////////////////////////////////////////////////////////////////////
// This function saves to flash
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_ControllerSaveToFlash(HANDLE Handle, int* Parameters, int* Buffers, int* SPPrograms, char* UserArrays);

//////////////////////////////////////////////////////////////////////////////////////////////////
// These functions are related to EtherCAT
//////////////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetEtherCATState(HANDLE Handle, int* State, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATError(HANDLE Handle, int* Error, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_MapEtherCATInput(HANDLE Handle, int Flags, int Offset, char* VariableName, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_MapEtherCATOutput(HANDLE Handle, int Flags, int Offset, char* VariableName, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_UnmapEtherCATInputsOutputs(HANDLE Handle, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATSlaveIndex(HANDLE Handle, int VendorID, int ProductID, int Count, double* SlaveIndex, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATSlaveOffset(HANDLE Handle, char* VariableName, int SlaveIndex, double* SlaveOffset, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATSlaveVendorID(HANDLE Handle, int SlaveIndex, double* VendorID, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATSlaveProductID(HANDLE Handle, int SlaveIndex, double* ProductID, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATSlaveRevision(HANDLE Handle, int SlaveIndex, double* Revision, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATSlaveType(HANDLE Handle, int VendorID, int ProductID, double* SlaveType, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetEtherCATSlaveState(HANDLE Handle, int SlaveIndex, double* SlaveState, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_DownloadFileOverEtherCAT(HANDLE Handle, char* Path, char* Filename, int SlaveIndex, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_ReadSDOValueOverEtherCAT(HANDLE Handle, int Flags, int SlaveIndex, int Index, int SubIndex, double* Value, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_WriteSDOValueOverEtherCAT(HANDLE Handle, int Flags, int SlaveIndex, int Index, int SubIndex, double Value, ACSC_WAITBLOCK* Wait);

////////////////////////////////////////////////////////////////////////////////////////
// These functions returns RAM / Flash Information                                    //
////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_GetVolatileMemoryUsage(HANDLE Handle, double* UsageInPercents, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetVolatileMemoryTotal(HANDLE Handle, double* TotalMemory, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetVolatileMemoryFree(HANDLE Handle, double* FreeMemory, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetNonVolatileMemoryUsage(HANDLE Handle, double* UsageInPercents, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetNonVolatileMemoryTotal(HANDLE Handle, double* TotalMemory, ACSC_WAITBLOCK* Wait);
int _ACSCLIB_ WINAPI acsc_GetNonVolatileMemoryFree(HANDLE Handle, double* FreeMemory, ACSC_WAITBLOCK* Wait);

////////////////////////////////////////////////////////////////////////////////////////
// These functions are used for starting / stopping SPiiPlusSC                        //
////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_StartSPiiPlusSC();
int _ACSCLIB_ WINAPI acsc_StopSPiiPlusSC();

////////////////////////////////////////////////////////////////////////////////////////
// These functions are used for starting / stopping SPiiPlus Simulator via RPC        //
////////////////////////////////////////////////////////////////////////////////////////
int _ACSCLIB_ WINAPI acsc_CloseSimulator();
HANDLE _ACSCLIB_ WINAPI acsc_OpenCommSimulator();

#else // defined (ACSC_RUNTIME_DYNAMIC_LINKING)

// function type definitions
typedef int (WINAPI *ACSC_AddMPoint)(HANDLE, int, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AddMPointM)(HANDLE, int*, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AddPoint)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AddPointM)(HANDLE, int*, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AppendBuffer)(HANDLE, int, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Arc1)(HANDLE, int*, double*, double*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Arc2)(HANDLE, int*, double*, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Break)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_BreakM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_CancelOperation)(HANDLE, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_CaptureComm)(HANDLE);
typedef int (WINAPI *ACSC_ClearBuffer)(HANDLE, int, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ClearVariables)(HANDLE, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_CloseComm)(HANDLE);
typedef int (WINAPI *ACSC_CloseHistoryBuffer)(HANDLE);
typedef int (WINAPI *ACSC_CloseLogFile)(HANDLE);
typedef int (WINAPI *ACSC_CloseSCLogFile)(HANDLE);
typedef int (WINAPI *ACSC_CloseMessageBuffer)(HANDLE);
typedef int (WINAPI *ACSC_Collect)(HANDLE, int, char*, int, int, char**, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Command)(HANDLE, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Commut)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_CommutExt)(HANDLE, int, float, int, int ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_CompileBuffer)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DeclareVariable)(HANDLE, int, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Disable)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DisableAll)(HANDLE, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DisableFault)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DisableM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DisableResponse)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DownloadBuffer)(HANDLE, int, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Enable)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_EnableFault)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_EnableM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_EnableResponse)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_EndSequence)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_EndSequenceM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ExtAddPoint)(HANDLE, int, double, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ExtAddPointM)(HANDLE, int*, double*, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ExtArc1)(HANDLE, int*, double*, double*, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ExtArc2)(HANDLE, int*, double*, double, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ExtLine)(HANDLE, int*, double*, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ExtToPoint)(HANDLE, int, int, double, double, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ExtToPointM)(HANDLE, int, int*, double*, double, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_FlushLogFile)(char*);
typedef int (WINAPI *ACSC_FlushSCLogFile)(char*);
typedef int (WINAPI *ACSC_GetAcceleration)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetAnalogInput)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetAnalogOutput)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetAxisState)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetCommOptions)(HANDLE, unsigned int*);
typedef int (WINAPI *ACSC_GetDeceleration)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetDefaultTimeout)(HANDLE);
typedef int	(WINAPI *ACSC_GetErrorString)(HANDLE, int, char*, int, int*);
typedef int (WINAPI *ACSC_GetExtInput)(HANDLE, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetExtInputPort)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetExtOutput)(HANDLE, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetExtOutputPort)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetFPosition)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetFVelocity)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetFault)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetFaultMask)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetFirmwareVersion)(HANDLE, char*, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetHistory)(HANDLE, char*, int, int*, BOOL);
typedef int (WINAPI *ACSC_GetIndexState)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetInput)(HANDLE, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetInputPort)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetInterruptMask)(HANDLE, int, unsigned int*);
typedef int (WINAPI *ACSC_GetCallbackMask)(HANDLE, int, unsigned __int64*);

typedef int (WINAPI *ACSC_GetJerk)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetKillDeceleration)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetLastError)();
typedef unsigned int (WINAPI *ACSC_GetLibraryVersion)();
typedef int (WINAPI *ACSC_GetMessage)(HANDLE, char*, int, int*, BOOL);
typedef int (WINAPI *ACSC_GetMotionError)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetMotorError)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetMotorState)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetOutput)(HANDLE, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetOutputPort)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetPCICards)(ACSC_PCI_SLOT*, int , int*); 
typedef int (WINAPI *ACSC_GetEthernetCards) (struct in_addr*,int,int*,unsigned long);
typedef int (WINAPI *ACSC_GetProgramError)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetProgramState)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetRPosition)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetRVelocity)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetResponseMask)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetSafetyInput)(HANDLE, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetSafetyInputPort)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetSafetyInputPortInv)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetSerialNumber)(HANDLE, char*, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetTimeout)(HANDLE);
typedef int (WINAPI *ACSC_GetVelocity)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Go)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GoM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Group)(HANDLE, int*, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_Halt)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_HaltM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Jog)(HANDLE, int, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_JogM)(HANDLE, int, int*, int*, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Kill)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_KillExt)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DisableExt)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_KillAll)(HANDLE, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_KillM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Line)(HANDLE, int*, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_LoadBuffer)(HANDLE, int, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_MultiPoint)(HANDLE, int, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_MultiPointM)(HANDLE, int, int*, double, ACSC_WAITBLOCK*);
typedef HANDLE (WINAPI *ACSC_OpenCommDirect)();
typedef int (WINAPI *ACSC_CloseSimulator)();
typedef HANDLE  (WINAPI *ACSC_OpenCommSimulator)();
typedef HANDLE (WINAPI *ACSC_OpenCommEthernet)(char*, int);
typedef HANDLE (WINAPI *ACSC_OpenCommEthernetUDP)(char*, int);
typedef HANDLE (WINAPI *ACSC_OpenCommEthernetTCP)(char*, int);
typedef HANDLE (WINAPI *ACSC_OpenCommSerial)(int, int);
typedef HANDLE (WINAPI *ACSC_OpenCommPCI)(int); 
typedef LP_ACSC_HISTORYBUFFER (WINAPI *ACSC_OpenHistoryBuffer)(HANDLE, int);
typedef int (WINAPI *ACSC_OpenLogFile)(HANDLE, char*);
typedef int (WINAPI *ACSC_OpenSCLogFile)(HANDLE, char*);
typedef LP_ACSC_HISTORYBUFFER (WINAPI *ACSC_OpenMessageBuffer)(HANDLE, int);
typedef int (WINAPI *ACSC_Projection)(HANDLE, int*, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ReadDPRAMInteger)(HANDLE, int, int*);
typedef int (WINAPI *ACSC_ReadDPRAMReal)(HANDLE, int, double*);
typedef int (WINAPI *ACSC_ReadInteger)(HANDLE, int, char*, int, int, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ReadReal)(HANDLE, int, char*, int, int, int, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Receive)(HANDLE, char*, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ReleaseComm)(HANDLE);
typedef int (WINAPI *ACSC_ResetIndexState)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_RunBuffer)(HANDLE, int, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Segment)(HANDLE, int, int*, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Send)(HANDLE, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetAcceleration)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetAccelerationImm)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetAnalogOutput)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetCallback)(HANDLE, ACSC_INTR_CALLBACK_FUNC, int);
typedef int (WINAPI *ACSC_SetCallbackPriority)(HANDLE, int);
typedef int (WINAPI *ACSC_SetCommOptions)(HANDLE, unsigned int);
typedef int (WINAPI *ACSC_SetDeceleration)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetDecelerationImm)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetExtOutput)(HANDLE, int, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetExtOutputPort)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetFPosition)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetFaultMask)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetInterruptMask)(HANDLE, int, unsigned int);
typedef int (WINAPI *ACSC_SetCallbackMask)(HANDLE, int, unsigned __int64);
typedef int (WINAPI *ACSC_SetIterations)(HANDLE, int);
typedef int (WINAPI *ACSC_SetJerk)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetJerkImm)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetKillDeceleration)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetKillDecelerationImm)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetMaster)(HANDLE, int, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetOutput)(HANDLE, int, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetOutputPort)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetRPosition)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetResponseMask)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetSafetyInputPortInv)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetTimeout)(HANDLE, int);
typedef int (WINAPI *ACSC_SetVelocity)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetVelocityImm)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Slave)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SlaveStalled)(HANDLE, int, int, double, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Spline)(HANDLE, int, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SplineM)(HANDLE, int, int*, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Split)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SplitAll)(HANDLE, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_StopBuffer)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_StopCollect)(HANDLE, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Stopper)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SuspendBuffer)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ToPoint)(HANDLE, int, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ToPointM)(HANDLE, int, int*, double*, ACSC_WAITBLOCK*);
typedef int	(WINAPI *ACSC_Transaction)(HANDLE, char*, int, char*, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_UploadBuffer)(HANDLE, int, int, char*, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_WaitCollectEnd)(HANDLE, int);
typedef int (WINAPI *ACSC_WaitCollectEndExt)(HANDLE, int, int);
typedef int (WINAPI *ACSC_WaitForAsyncCall)(HANDLE, void*, int*, ACSC_WAITBLOCK*, int);
typedef int (WINAPI *ACSC_WaitInput)(HANDLE, int, int, int, int);
typedef int (WINAPI *ACSC_WaitLogicalMotionEnd)(HANDLE, int, int);
typedef int (WINAPI *ACSC_WaitMotionEnd)(HANDLE, int, int);
typedef int (WINAPI *ACSC_WaitMotorEnabled)(HANDLE, int, int, int);
typedef int (WINAPI *ACSC_WaitMotorCommutated)(HANDLE, int, int, int);
typedef int (WINAPI *ACSC_WaitProgramEnd)(HANDLE, int, int);
typedef int (WINAPI *ACSC_WaitUserCondition)(HANDLE, ACSC_USER_CONDITION_FUNC, int);
typedef int (WINAPI *ACSC_WriteDPRAMInteger)(HANDLE, int, int);
typedef int (WINAPI *ACSC_WriteDPRAMReal)(HANDLE, int, double);
typedef int (WINAPI *ACSC_WriteInteger)(HANDLE, int, char*, int, int, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_WriteLogFile)(HANDLE, char*, int);
typedef int (WINAPI *ACSC_WriteSCLogFile)(HANDLE, char*, int);
typedef int (WINAPI *ACSC_WriteReal)(HANDLE, int, char*, int, int, int, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_LoadBufferIgnoreServiceLines)(HANDLE, int, char*, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_LoadBuffersFromFile)(HANDLE, char*, ACSC_WAITBLOCK*);

typedef int (WINAPI *ACSC_PegI)(HANDLE, int, int, double, int, int, int, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_PegR)(HANDLE, int, int, double, char*, char*, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_PegInc)(HANDLE, int, int, double, double, double, double, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_PegRandom)(HANDLE, int, int, double, char*, char*, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AssignPins)(HANDLE, int, unsigned short, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_StopPeg)(HANDLE, int, ACSC_WAITBLOCK*);

typedef int (WINAPI *ACSC_AssignPegNT)(HANDLE Handle, int Axis, int EngToEncBitCode, int GpOutsBitCode, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_AssignPegOutputsNT)(HANDLE Handle, int Axis, int OutputIndex, int BitCode, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_AssignFastInputsNT)(HANDLE Handle, int Axis, int InputIndex, int BitCode, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_PegIncNT)(HANDLE Handle, int Flags, int Axis, double Width, double FirstPoint, double Interval, double LastPoint, int TbNumber, double TbPeriod, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_PegRandomNT)(HANDLE Handle, int Flags, int Axis, double Width, int Mode, int FirstIndex, int LastIndex, char* PointArray, char* StateArray, int TbNumber, double TbPeriod, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_WaitPegReadyNT)(HANDLE Handle, int Axis, int Timeout);
typedef int (WINAPI *ACSC_StartPegNT)(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_StopPegNT)(HANDLE Handle, int Axis, ACSC_WAITBLOCK* Wait);

typedef int (WINAPI *ACSC_CollectB)(HANDLE, int, char*, int, int, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DataCollection)(HANDLE, int, int, char*, int, int, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_DataCollectionExt)(HANDLE Handle, int Flags, int Axis, char* Array, int NSample, double Period, char* Vars, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_AddPVPoint)(HANDLE, int, double, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AddPVPointM)(HANDLE, int*, double*, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AddPVTPoint)(HANDLE, int, double, double, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_AddPVTPointM)(HANDLE, int*, double*, double*, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_LoadFileToRealVariable)(HANDLE, int, char*, int, int, int, int, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_LoadFileToIntegerVariable)(HANDLE, int, char*, int, int, int, int, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_LoadDataToController)(HANDLE,int , char* , int, int, int, int, char*, int, BOOL,ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_UploadDataFromController)(HANDLE,int,char*,int,int,int,int,int,char*,char*,BOOL,ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetQueueOverflowTimeout)(HANDLE, int);
typedef int (WINAPI *ACSC_GetQueueOverflowTimeout)(HANDLE);
typedef int (WINAPI *ACSC_SetTargetPosition)(HANDLE, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetTargetPosition)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetTargetPositionM)(HANDLE, int*, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Track)(HANDLE, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_TrackM)(HANDLE, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_FaultClearM)(HANDLE, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_FaultClear)(HANDLE, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Getconf)(HANDLE, int, int, int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_Setconf)(HANDLE, int, int, int, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetCallbackExt)(HANDLE, ACSC_INTR_CALLBACK_FUNC_EXT, void*, int);
typedef int (WINAPI *ACSC_InstallCallback)(HANDLE, ACSC_USER_CALLBACK_FUNCTION, void*, int);
typedef int (WINAPI *ACSC_DownloadBinVariableToFile)(HANDLE, int, char*, int, int, int, int, int, char*, char*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetLogFileOptions)(HANDLE, ACSC_LOG_DETALIZATION_LEVEL, ACSC_LOG_DATA_PRESENTATION);

typedef int (WINAPI *ACSC_GetConf)(HANDLE, int, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetConf)(HANDLE, int, int, double, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SysInfo)(HANDLE Handle, int Key, double *Value, ACSC_WAITBLOCK* Wait);

typedef int (WINAPI *ACSC_GetAxesCount)(HANDLE Handle, double *Value, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_GetBuffersCount)(HANDLE Handle, double *Value, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_GetDBufferIndex)(HANDLE Handle, double *Value, ACSC_WAITBLOCK* Wait);

typedef int (WINAPI *ACSC_SetServer)(char *IP);
typedef int (WINAPI *ACSC_SetServerExt)(char*,int);
typedef int (WINAPI *ACSC_SetServerExtLogin)(char*,int,char*,char*,char*);
typedef int (WINAPI *ACSC_GetSingleMessage)(HANDLE Handle, char* Buf, int Count, int* Received, int Timeout);

typedef int (WINAPI *ACSC_GetConnectionsList)(ACSC_CONNECTION_DESC* ConnectionsList, int MaxNumConnections, int* NumConnections);
typedef int (WINAPI *ACSC_GetConnectionInfo)(HANDLE Handle, ACSC_CONNECTION_INFO* ConnectionInfo);
typedef int (WINAPI *ACSC_TerminateConnection)(ACSC_CONNECTION_DESC* Connection);

typedef int (WINAPI *ACSC_GetLogData)(HANDLE Handle, char* Buf, int Count, int* Received);

typedef int (WINAPI *ACSC_RegisterEmergencyStop)();
typedef int (WINAPI *ACSC_UnregisterEmergencyStop)();

typedef unsigned int (WINAPI *ACSC_GetUMDVersion)();

typedef int (WINAPI *ACSC_AnalyzeApplication)(HANDLE, const char*, ACSC_APPSL_INFO**, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_FreeApplication)(ACSC_APPSL_INFO*);
typedef int (WINAPI *ACSC_SaveApplication)(HANDLE, const char*, ACSC_APPSL_INFO*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_LoadApplication)(HANDLE, const char*, ACSC_APPSL_INFO*, ACSC_WAITBLOCK*);

typedef int (WINAPI *ACSC_ControllerReboot)(HANDLE, int);
typedef int (WINAPI *ACSC_ControllerFactoryDefault)(HANDLE, int);
typedef int (WINAPI *ACSC_ControllerSaveToFlash)(HANDLE, int*, int*, int*, char*);

typedef int (WINAPI *ACSC_GetSharedMemoryAddress)(HANDLE, int, char*, unsigned int*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_ReadSharedMemoryReal)(HANDLE, unsigned int, int, int, int, int, double*);
typedef int (WINAPI *ACSC_ReadSharedMemoryInteger)(HANDLE, unsigned int, int, int, int, int, int*);
typedef int (WINAPI *ACSC_WriteSharedMemoryReal)(HANDLE, unsigned int, int, int, int, int, double*);
typedef int (WINAPI *ACSC_WriteSharedMemoryInteger)(HANDLE, unsigned int, int, int, int, int, int*);

typedef HANDLE (WINAPI *ACSC_GetEtherCATState)(HANDLE Handle, int* State, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATError)(HANDLE Handle, int* Error, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_MapEtherCATInput)(HANDLE Handle, int Flags, int Offset, char* VariableName, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_MapEtherCATOutput)(HANDLE Handle, int Flags, int Offset, char* VariableName, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_UnmapEtherCATInputsOutputs)(HANDLE Handle, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATSlaveIndex)(HANDLE Handle, int VendorID, int ProductID, int Count, int* SlaveIndex, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATSlaveOffset)(HANDLE Handle, char* VariableName, int SlaveIndex, double* SlaveOffset, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATSlaveVendorID)(HANDLE Handle, int SlaveIndex, double* VendorID, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATSlaveProductID)(HANDLE Handle, int SlaveIndex, double* ProductID, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATSlaveRevision)(HANDLE Handle, int SlaveIndex, double* Revision, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATSlaveType)(HANDLE Handle, int SlaveIndex, double* SlaveType, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_GetEtherCATSlaveState)(HANDLE Handle, int SlaveIndex, double* SlaveState, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_DownloadFileOverEtherCAT)(HANDLE Handle, char* Path, char* Filename, int SlaveIndex, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_ReadSDOValueOverEtherCAT)(HANDLE Handle, int Flags, int SlaveIndex, int Index, int SubIndex, double* Value, ACSC_WAITBLOCK* Wait);
typedef HANDLE (WINAPI *ACSC_WriteSDOValueOverEtherCAT)(HANDLE Handle, int Flags, int SlaveIndex, int Index, int SubIndex, double Value, ACSC_WAITBLOCK* Wait);

typedef int (WINAPI *ACSC_CopyFileToController)(HANDLE Handle, char* SourceFileName, char* DestinationFileName, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_DeleteFileFromController)(HANDLE Handle, char* FileName, ACSC_WAITBLOCK* Wait);

typedef int (WINAPI *ACSC_SegmentedMotion)(HANDLE Handle, int Flags, int* Axes, double* Point, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_ExtendedSegmentedMotion)(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, double JunctionVelocity, double Angle, double StarvationMargin, char* Segments, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_ExtendedSegmentedMotionExt)(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, double JunctionVelocity, double Angle, double CurveVelocity, double Deviation, double Radius, double MaxLength, double StarvationMargin, char* Segments, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_SegmentLine)(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_SegmentLineExt)(HANDLE Handle, int Flags, int* Axes, double* Point, double Velocity, double EndVelocity, double Time, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_SegmentArc1)(HANDLE Handle, int Flags, int* Axes, double* Center, double* FinalPoint, int Rotation, double Velocity, double EndVelocity, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_SegmentArc2)(HANDLE Handle, int Flags, int* Axes, double* Center, double Angle, double Velocity, double EndVelocity, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_SegmentArc1Ext)(HANDLE Handle, int Flags, int* Axes, double* Center, double* FinalPoint, int Rotation, double Velocity, double EndVelocity, double Time, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_SegmentArc2Ext)(HANDLE Handle, int Flags, int* Axes, double* Center, double Angle, double Velocity, double EndVelocity, double Time, char* Values, char* Variables, int Index, char* Masks, ACSC_WAITBLOCK* Wait);
typedef int (WINAPI *ACSC_acsc_BlendedSegmentMotion)(HANDLE Handle, int Flags, int* Axes, double* Point, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK *Wait)
typedef int (WINAPI *ACSC_BlendedLine)(HANDLE Handle, int Flags, int* Axes,double* Point, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK* Wait)
typedef int (WINAPI *ACSC_BlendedArc1)(HANDLE Handle, int Flags, int* Axes, double* Center, double* FinalPoint, int Rotation, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK* Wait)
typedef int (WINAPI *ACSC_BlendedArc2)(HANDLE Handle, int Flags, int* Axes, double* Center, double Angle, double SegmentTime, double AccelerationTime, double JerkTime, double DwellTime, ACSC_WAITBLOCK* Wait)
typedef int (WINAPI *ACSC_GetAnalogInputNT)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetAnalogOutputNT)(HANDLE, int, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_SetAnalogOutputNT)(HANDLE, int, double, ACSC_WAITBLOCK*);

typedef int (WINAPI *ACSC_GetVolatileMemoryUsage)(HANDLE, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetVolatileMemoryTotal)(HANDLE, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetVolatileMemoryFree)(HANDLE, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetNonVolatileMemoryUsage)(HANDLE, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetNonVolatileMemoryTotal)(HANDLE, double*, ACSC_WAITBLOCK*);
typedef int (WINAPI *ACSC_GetNonVolatileMemoryFree)(HANDLE, double*, ACSC_WAITBLOCK*);

typedef int (WINAPI *ACSC_StartSPiiPlusSC)();
typedef int (WINAPI *ACSC_StopSPiiPlusSC)();


#if !defined (ACSC_RUNTIME_DYNAMIC_VARIABLES)
ACSC_AddMPoint							acsc_AddMPoint;
ACSC_AddMPointM							acsc_AddMPointM;
ACSC_AddPoint							acsc_AddPoint;
ACSC_AddPointM							acsc_AddPointM;
ACSC_AppendBuffer						acsc_AppendBuffer;
ACSC_Arc1								acsc_Arc1;
ACSC_Arc2								acsc_Arc2;
ACSC_Break								acsc_Break;
ACSC_BreakM								acsc_BreakM;
ACSC_CancelOperation					acsc_CancelOperation;
ACSC_CaptureComm						acsc_CaptureComm;
ACSC_ClearBuffer						acsc_ClearBuffer;
ACSC_ClearVariables						acsc_ClearVariables;
ACSC_CloseComm							acsc_CloseComm;
ACSC_CloseHistoryBuffer					acsc_CloseHistoryBuffer;
ACSC_CloseLogFile						acsc_CloseLogFile;
ACSC_CloseSCLogFile						acsc_CloseSCLogFile;
ACSC_CloseMessageBuffer					acsc_CloseMessageBuffer;
ACSC_Collect							acsc_Collect;
ACSC_Command							acsc_Command;
ACSC_Commut								acsc_Commut;
ACSC_CommutExt							acsc_CommutExt;
ACSC_CompileBuffer						acsc_CompileBuffer;
ACSC_DeclareVariable					acsc_DeclareVariable;
ACSC_Disable							acsc_Disable;
ACSC_DisableAll							acsc_DisableAll;
ACSC_DisableFault						acsc_DisableFault;
ACSC_DisableM							acsc_DisableM;
ACSC_DisableResponse					acsc_DisableResponse;
ACSC_DownloadBuffer						acsc_DownloadBuffer;
ACSC_Enable								acsc_Enable;
ACSC_EnableFault						acsc_EnableFault;
ACSC_EnableM							acsc_EnableM;
ACSC_EnableResponse						acsc_EnableResponse;
ACSC_EndSequence						acsc_EndSequence;
ACSC_EndSequenceM						acsc_EndSequenceM;
ACSC_ExtAddPoint						acsc_ExtAddPoint;
ACSC_ExtAddPointM						acsc_ExtAddPointM;
ACSC_ExtArc1							acsc_ExtArc1;
ACSC_ExtArc2							acsc_ExtArc2;
ACSC_ExtLine							acsc_ExtLine;
ACSC_ExtToPoint							acsc_ExtToPoint;
ACSC_ExtToPointM						acsc_ExtToPointM;
ACSC_FlushLogFile						acsc_FlushLogFile;
ACSC_FlushSCLogFile						acsc_FlushSCLogFile;
ACSC_GetAcceleration					acsc_GetAcceleration;
ACSC_GetAnalogInput						acsc_GetAnalogInput;
ACSC_GetAnalogOutput					acsc_GetAnalogOutput;
ACSC_GetAxisState						acsc_GetAxisState;
ACSC_GetCommOptions						acsc_GetCommOptions;
ACSC_GetDeceleration					acsc_GetDeceleration;
ACSC_GetDefaultTimeout					acsc_GetDefaultTimeout;
ACSC_GetErrorString						acsc_GetErrorString;
ACSC_GetExtInput						acsc_GetExtInput;
ACSC_GetExtInputPort					acsc_GetExtInputPort;
ACSC_GetExtOutput						acsc_GetExtOutput;
ACSC_GetExtOutputPort					acsc_GetExtOutputPort;
ACSC_GetFPosition						acsc_GetFPosition;
ACSC_GetFVelocity						acsc_GetFVelocity;
ACSC_GetFault							acsc_GetFault;
ACSC_GetFaultMask						acsc_GetFaultMask;
ACSC_GetFirmwareVersion					acsc_GetFirmwareVersion;
ACSC_GetHistory							acsc_GetHistory;
ACSC_GetIndexState						acsc_GetIndexState;
ACSC_GetInput							acsc_GetInput;
ACSC_GetInputPort						acsc_GetInputPort;
ACSC_GetInterruptMask					acsc_GetInterruptMask;
ACSC_GetCallbackMask					acsc_GetCallbackMask;
ACSC_GetJerk							acsc_GetJerk;
ACSC_GetKillDeceleration				acsc_GetKillDeceleration;
ACSC_GetLastError						acsc_GetLastError;
ACSC_GetLibraryVersion					acsc_GetLibraryVersion;
ACSC_GetMessage							acsc_GetMessage;
ACSC_GetMotionError						acsc_GetMotionError;
ACSC_GetMotorError						acsc_GetMotorError;
ACSC_GetMotorState						acsc_GetMotorState;
ACSC_GetOutput							acsc_GetOutput;
ACSC_GetOutputPort						acsc_GetOutputPort;
ACSC_GetPCICards						acsc_GetPCICards;
ACSC_GetEthernetCards                   acsc_GetEthernetCards;
ACSC_GetProgramError					acsc_GetProgramError;
ACSC_GetProgramState					acsc_GetProgramState;
ACSC_GetRPosition						acsc_GetRPosition;
ACSC_GetRVelocity						acsc_GetRVelocity;
ACSC_GetResponseMask					acsc_GetResponseMask;
ACSC_GetSafetyInput						acsc_GetSafetyInput;
ACSC_GetSafetyInputPort					acsc_GetSafetyInputPort;
ACSC_GetSafetyInputPortInv				acsc_GetSafetyInputPortInv;
ACSC_GetSerialNumber					acsc_GetSerialNumber;
ACSC_GetTimeout							acsc_GetTimeout;
ACSC_GetVelocity						acsc_GetVelocity;
ACSC_Go									acsc_Go;
ACSC_GoM								acsc_GoM;
ACSC_Group								acsc_Group;
ACSC_Halt								acsc_Halt;
ACSC_HaltM								acsc_HaltM;
ACSC_Jog								acsc_Jog;
ACSC_JogM								acsc_JogM;
ACSC_Kill								acsc_Kill;
ACSC_KillExt							acsc_KillExt;
ACSC_DisableExt							acsc_DisableExt;
ACSC_KillAll							acsc_KillAll;
ACSC_KillM								acsc_KillM;
ACSC_Line								acsc_Line;
ACSC_LoadBuffer							acsc_LoadBuffer;
ACSC_MultiPoint							acsc_MultiPoint;
ACSC_MultiPointM						acsc_MultiPointM;
#if defined(WIN32) && !defined(UNDER_RTSS)
ACSC_OpenCommDirect						acsc_OpenCommDirect;
ACSC_CloseSimulator						acsc_CloseSimulator;
ACSC_OpenCommSimulator					acsc_OpenCommSimulator;
ACSC_OpenCommEthernet					acsc_OpenCommEthernet;
ACSC_OpenCommEthernetUDP				acsc_OpenCommEthernetUDP;
ACSC_OpenCommEthernetTCP				acsc_OpenCommEthernetTCP;
ACSC_OpenCommSerial						acsc_OpenCommSerial;
#endif
ACSC_OpenCommPCI						acsc_OpenCommPCI;
ACSC_OpenHistoryBuffer					acsc_OpenHistoryBuffer;
ACSC_OpenLogFile						acsc_OpenLogFile;
ACSC_OpenSCLogFile						acsc_OpenSCLogFile;
ACSC_OpenMessageBuffer					acsc_OpenMessageBuffer;
ACSC_Projection							acsc_Projection;
ACSC_ReadDPRAMInteger					acsc_ReadDPRAMInteger;
ACSC_ReadDPRAMReal						acsc_ReadDPRAMReal;
ACSC_ReadInteger						acsc_ReadInteger;
ACSC_ReadReal							acsc_ReadReal;
ACSC_Receive							acsc_Receive;
ACSC_ReleaseComm						acsc_ReleaseComm;
ACSC_ResetIndexState					acsc_ResetIndexState;
ACSC_RunBuffer							acsc_RunBuffer;
ACSC_Segment							acsc_Segment;
ACSC_Send								acsc_Send;
ACSC_SetAcceleration					acsc_SetAcceleration;
ACSC_SetAccelerationImm					acsc_SetAccelerationImm;
ACSC_SetAnalogOutput					acsc_SetAnalogOutput;
ACSC_SetCallback						acsc_SetCallback;
ACSC_SetCallbackPriority				acsc_SetCallbackPriority;
ACSC_SetCommOptions						acsc_SetCommOptions;
ACSC_SetDeceleration					acsc_SetDeceleration;
ACSC_SetDecelerationImm					acsc_SetDecelerationImm;
ACSC_SetExtOutput						acsc_SetExtOutput;
ACSC_SetExtOutputPort					acsc_SetExtOutputPort;
ACSC_SetFPosition						acsc_SetFPosition;
ACSC_SetFaultMask						acsc_SetFaultMask;
ACSC_SetInterruptMask					acsc_SetInterruptMask;
ACSC_SetCallbackMask					acsc_SetCallbackMask;
ACSC_SetIterations						acsc_SetIterations;
ACSC_SetJerk							acsc_SetJerk;
ACSC_SetJerkImm							acsc_SetJerkImm;
ACSC_SetKillDeceleration				acsc_SetKillDeceleration;
ACSC_SetKillDecelerationImm				acsc_SetKillDecelerationImm;
ACSC_SetMaster							acsc_SetMaster;
ACSC_SetOutput							acsc_SetOutput;
ACSC_SetOutputPort						acsc_SetOutputPort;
ACSC_SetRPosition						acsc_SetRPosition;
ACSC_SetResponseMask					acsc_SetResponseMask;
ACSC_SetSafetyInputPortInv				acsc_SetSafetyInputPortInv;
ACSC_SetTimeout							acsc_SetTimeout;
ACSC_SetVelocity						acsc_SetVelocity;
ACSC_SetVelocityImm						acsc_SetVelocityImm;
ACSC_Slave								acsc_Slave;
ACSC_SlaveStalled						acsc_SlaveStalled;
ACSC_Spline								acsc_Spline;
ACSC_SplineM							acsc_SplineM;
ACSC_Split								acsc_Split;
ACSC_SplitAll							acsc_SplitAll;
ACSC_StopBuffer							acsc_StopBuffer;
ACSC_StopCollect						acsc_StopCollect;
ACSC_Stopper							acsc_Stopper;
ACSC_SuspendBuffer						acsc_SuspendBuffer;
ACSC_ToPoint							acsc_ToPoint;
ACSC_ToPointM							acsc_ToPointM;
ACSC_Transaction						acsc_Transaction;
ACSC_UploadBuffer						acsc_UploadBuffer;
ACSC_WaitCollectEnd						acsc_WaitCollectEnd;
ACSC_WaitCollectEndExt					acsc_WaitCollectEndExt;
ACSC_WaitForAsyncCall					acsc_WaitForAsyncCall;
ACSC_WaitInput							acsc_WaitInput;
ACSC_WaitLogicalMotionEnd				acsc_WaitLogicalMotionEnd;
ACSC_WaitMotionEnd						acsc_WaitMotionEnd;
ACSC_WaitMotorEnabled					acsc_WaitMotorEnabled;
ACSC_WaitMotorCommutated				acsc_WaitMotorCommutated;
ACSC_WaitProgramEnd						acsc_WaitProgramEnd;
ACSC_WaitUserCondition					acsc_WaitUserCondition;
ACSC_WriteDPRAMInteger					acsc_WriteDPRAMInteger;
ACSC_WriteDPRAMReal						acsc_WriteDPRAMReal;
ACSC_WriteInteger						acsc_WriteInteger;
ACSC_WriteLogFile						acsc_WriteLogFile;
ACSC_WriteSCLogFile						acsc_WriteSCLogFile;
ACSC_WriteReal							acsc_WriteReal;
ACSC_LoadBufferIgnoreServiceLines		acsc_LoadBufferIgnoreServiceLines;
ACSC_LoadBuffersFromFile				acsc_LoadBuffersFromFile;

ACSC_PegI								acsc_PegI;
ACSC_PegR								acsc_PegR;
ACSC_PegInc								acsc_PegInc;
ACSC_PegRandom							acsc_PegRandom;
ACSC_AssignPins							acsc_AssignPins;
ACSC_StopPeg							acsc_StopPeg;

ACSC_AssignPegNT						acsc_AssignPegNT;
ACSC_AssignPegOutputsNT					acsc_AssignPegOutputsNT;
ACSC_AssignFastInputsNT					acsc_AssignFastInputsNT;
ACSC_PegIncNT							acsc_PegIncNT;
ACSC_PegRandomNT						acsc_PegRandomNT;
ACSC_WaitPegReadyNT						acsc_WaitPegReadyNT;
ACSC_StartPegNT							acsc_StartPegNT;
ACSC_StopPegNT							acsc_StopPegNT;

ACSC_CollectB							acsc_CollectB;
ACSC_DataCollection                     acsc_DataCollection;
ACSC_DataCollectionExt					acsc_DataCollectionExt;
ACSC_AddPVPoint							acsc_AddPVPoint;
ACSC_AddPVPointM						acsc_AddPVPointM;
ACSC_AddPVTPoint						acsc_AddPVTPoint;
ACSC_AddPVTPointM						acsc_AddPVTPointM;
ACSC_LoadFileToRealVariable				acsc_LoadFileToRealVariable;
ACSC_LoadFileToIntegerVariable			acsc_LoadFileToIntegerVariable;
ACSC_LoadDataToController               acsc_LoadDataToController;
ACSC_UploadDataFromController           acsc_UploadDataFromController;
ACSC_SetQueueOverflowTimeout			acsc_SetQueueOverflowTimeout;
ACSC_GetQueueOverflowTimeout			acsc_GetQueueOverflowTimeout;
ACSC_SetTargetPosition					acsc_SetTargetPosition;
ACSC_GetTargetPosition					acsc_GetTargetPosition;
ACSC_SetTargetPositionM					acsc_SetTargetPositionM;
ACSC_Track								acsc_Track;
ACSC_TrackM								acsc_TrackM;
ACSC_FaultClearM						acsc_FaultClearM;
ACSC_FaultClear							acsc_FaultClear;
ACSC_Getconf							acsc_Getconf;
ACSC_Setconf							acsc_Setconf;
ACSC_GetConf							acsc_GetConf;
ACSC_SetConf							acsc_SetConf;
ACSC_SysInfo							acsc_SysInfo;

ACSC_GetAxesCount						acsc_GetAxesCount;
ACSC_GetBuffersCount					acsc_GetBuffersCount;
ACSC_GetDBufferIndex					acsc_GetDBufferIndex;

ACSC_SetCallbackExt						acsc_SetCallbackExt;
ACSC_InstallCallback					acsc_InstallCallback;
ACSC_DownloadBinVariableToFile			acsc_DownloadBinVariableToFile;
ACSC_SetLogFileOptions					acsc_SetLogFileOptions;

ACSC_SetServer							acsc_SetServer;
ACSC_SetServerExt					    acsc_SetServerExt;
ACSC_SetServerExtLogin					acsc_SetServerExtLogin;

ACSC_GetSingleMessage					acsc_GetSingleMessage;

ACSC_GetConnectionsList			    	acsc_GetConnectionsList;
ACSC_GetConnectionInfo			    	acsc_GetConnectionInfo;
ACSC_TerminateConnection				acsc_TerminateConnection;

ACSC_GetLogData							acsc_GetLogData;

ACSC_RegisterEmergencyStop              acsc_RegisterEmergencyStop;
ACSC_UnregisterEmergencyStop			acsc_UnregisterEmergencyStop;

ACSC_GetUMDVersion						acsc_GetUMDVersion;

ACSC_AnalyzeApplication                 acsc_AnalyzeApplication; 
ACSC_FreeApplication		        	acsc_FreeApplication;	
ACSC_SaveApplication                    acsc_SaveApplication;    
ACSC_LoadApplication		        	acsc_LoadApplication;	

ACSC_ControllerReboot					acsc_ControllerReboot;
ACSC_ControllerFactoryDefault			acsc_ControllerFactoryDefault;
ACSC_ControllerSaveToFlash				acsc_ControllerSaveToFlash;

ACSC_GetSharedMemoryAddress				acsc_GetSharedMemoryAddress;
ACSC_ReadSharedMemoryReal				acsc_ReadSharedMemoryReal;
ACSC_ReadSharedMemoryInteger			acsc_ReadSharedMemoryInteger;
ACSC_WriteSharedMemoryReal				acsc_WriteSharedMemoryReal;
ACSC_WriteSharedMemoryInteger			acsc_WriteSharedMemoryInteger;

ACSC_GetEtherCATState					acsc_GetEtherCATState;
ACSC_GetEtherCATError					acsc_GetEtherCATError;
ACSC_MapEtherCATInput					acsc_MapEtherCATInput;
ACSC_MapEtherCATOutput					acsc_MapEtherCATOutput;
ACSC_UnmapEtherCATInputsOutputs			acsc_UnmapEtherCATInputsOutputs;
ACSC_GetEtherCATSlaveIndex				acsc_GetEtherCATSlaveIndex;
ACSC_GetEtherCATSlaveOffset				acsc_GetEtherCATSlaveOffset;
ACSC_GetEtherCATSlaveVendorID			acsc_GetEtherCATSlaveVendorID;
ACSC_GetEtherCATSlaveProductID			acsc_GetEtherCATSlaveProductID;
ACSC_GetEtherCATSlaveRevision			acsc_GetEtherCATSlaveRevision;
ACSC_GetEtherCATSlaveType				acsc_GetEtherCATSlaveType;
ACSC_GetEtherCATSlaveState				acsc_GetEtherCATSlaveState;
ACSC_DownloadFileOverEtherCAT			acsc_DownloadFileOverEtherCAT;
ACSC_ReadSDOValueOverEtherCAT			acsc_ReadSDOValueOverEtherCAT;
ACSC_WriteSDOValueOverEtherCAT			acsc_WriteSDOValueOverEtherCAT;

ACSC_CopyFileToController				acsc_CopyFileToController;
ACSC_DeleteFileFromController			acsc_DeleteFileFromController;

ACSC_SegmentedMotion					acsc_SegmentedMotion;
ACSC_ExtendedSegmentedMotion			acsc_ExtendedSegmentedMotion;
ACSC_ExtendedSegmentedMotionExt			acsc_ExtendedSegmentedMotionExt;
ACSC_SegmentLine						acsc_SegmentLine;
ACSC_SegmentLineExt						acsc_SegmentLineExt;
ACSC_SegmentArc1						acsc_SegmentArc1;
ACSC_SegmentArc1Ext						acsc_SegmentArc1Ext;
ACSC_SegmentArc2						acsc_SegmentArc2;
ACSC_SegmentArc2Ext						acsc_SegmentArc2Ext;
ACSC_BlendedSegmentMotion				acsc_BlendedSegmentMotion;
ACSC_BlendedLine						acsc_BlendedLine;
ACSC_BlendedArc1						acsc_BlendedArc1;
ACSC_BlendedArc2						acsc_BlendedArc2;

ACSC_GetAnalogInputNT					acsc_GetAnalogInputNT;
ACSC_GetAnalogOutputNT					acsc_GetAnalogOutputNT;
ACSC_SetAnalogOutputNT					acsc_SetAnalogOutputNT;

ACSC_GetVolatileMemoryUsage				acsc_GetVolatileMemoryUsage;
ACSC_GetVolatileMemoryTotal				acsc_GetVolatileMemoryTotal;
ACSC_GetVolatileMemoryFree				acsc_GetVolatileMemoryFree;
ACSC_GetNonVolatileMemoryUsage			acsc_GetNonVolatileMemoryUsage;
ACSC_GetNonVolatileMemoryTotal			acsc_GetNonVolatileMemoryTotal;
ACSC_GetNonVolatileMemoryFree			acsc_GetNonVolatileMemoryFree;

ACSC_StartSPiiPlusSC					acsc_StartSPiiPlusSC;
ACSC_StopSPiiPlusSC						acsc_StopSPiiPlusSC;


static HMODULE hACSCLibraryModule;

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function loads ACSCL.DLL and obtains addresses for all exported functions.
// Call this function before any using of ACSC API.
// Check return value for success.
//////////////////////////////////////////////////////////////////////////////////////////////////
static int InitACSCLibrary()
{
	hACSCLibraryModule = LoadLibrary("ACSCL.dll");

	if (hACSCLibraryModule == NULL)
		return 0;

	acsc_AddMPoint = (ACSC_AddMPoint) GetProcAddress(hACSCLibraryModule, "_acsc_AddMPoint@20");																//	   2
	acsc_AddMPointM = (ACSC_AddMPointM) GetProcAddress(hACSCLibraryModule, "_acsc_AddMPointM@20");															//     3
	acsc_AddPoint = (ACSC_AddPoint) GetProcAddress(hACSCLibraryModule, "_acsc_AddPoint@20");																//     4
	acsc_AddPointM = (ACSC_AddPointM) GetProcAddress(hACSCLibraryModule, "_acsc_AddPointM@16");																//	   5
	acsc_AppendBuffer = (ACSC_AppendBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_AppendBuffer@20");													//	   6
	acsc_Arc1 = (ACSC_Arc1) GetProcAddress(hACSCLibraryModule, "_acsc_Arc1@24");																			//	   7
	acsc_Arc2 = (ACSC_Arc2) GetProcAddress(hACSCLibraryModule, "_acsc_Arc2@24");																			//	   8
	acsc_Break = (ACSC_Break) GetProcAddress(hACSCLibraryModule, "_acsc_Break@12");																			//     9
	acsc_BreakM = (ACSC_BreakM) GetProcAddress(hACSCLibraryModule, "_acsc_BreakM@12");																		//     10
	acsc_CancelOperation = (ACSC_CancelOperation) GetProcAddress(hACSCLibraryModule, "_acsc_CancelOperation@8");											//     11
	acsc_CaptureComm = (ACSC_CaptureComm) GetProcAddress(hACSCLibraryModule, "_acsc_CaptureComm@4");														//     12
	acsc_ClearBuffer = (ACSC_ClearBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_ClearBuffer@20");														//     13
	acsc_ClearVariables = (ACSC_ClearVariables) GetProcAddress(hACSCLibraryModule, "_acsc_ClearVariables@8");												//     14
	acsc_CloseComm = (ACSC_CloseComm) GetProcAddress(hACSCLibraryModule, "_acsc_CloseComm@4");																//     15
	acsc_CloseHistoryBuffer = (ACSC_CloseHistoryBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_CloseHistoryBuffer@4");									//     16
	acsc_CloseLogFile = (ACSC_CloseLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_CloseLogFile@4");														//     17
	acsc_CloseMessageBuffer = (ACSC_CloseMessageBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_CloseMessageBuffer@4");									//     18
	acsc_Collect = (ACSC_Collect) GetProcAddress(hACSCLibraryModule, "_acsc_Collect@28");																	//     19
	acsc_Command = (ACSC_Command) GetProcAddress(hACSCLibraryModule, "_acsc_Command@16");																	//     20
	acsc_CompileBuffer = (ACSC_CompileBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_CompileBuffer@12");													//     21
	acsc_DeclareVariable = (ACSC_DeclareVariable) GetProcAddress(hACSCLibraryModule, "_acsc_DeclareVariable@16");											//     22
	acsc_Disable = (ACSC_Disable) GetProcAddress(hACSCLibraryModule, "_acsc_Disable@12");																	//     23
	acsc_DisableAll = (ACSC_DisableAll) GetProcAddress(hACSCLibraryModule, "_acsc_DisableAll@8");															//     24
	acsc_DisableFault = (ACSC_DisableFault) GetProcAddress(hACSCLibraryModule, "_acsc_DisableFault@16");													//     25
	acsc_DisableM = (ACSC_DisableM) GetProcAddress(hACSCLibraryModule, "_acsc_DisableM@12");																//     26
	acsc_DisableResponse = (ACSC_DisableResponse) GetProcAddress(hACSCLibraryModule, "_acsc_DisableResponse@16");											//     27
	acsc_DownloadBuffer = (ACSC_DownloadBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_DownloadBuffer@20");												//     28
	acsc_Enable = (ACSC_Enable) GetProcAddress(hACSCLibraryModule, "_acsc_Enable@12");																		//     29
	acsc_EnableFault = (ACSC_EnableFault) GetProcAddress(hACSCLibraryModule, "_acsc_EnableFault@16");														//     30
	acsc_EnableM = (ACSC_EnableM) GetProcAddress(hACSCLibraryModule, "_acsc_EnableM@12");																	//     31
	acsc_EnableResponse = (ACSC_EnableResponse) GetProcAddress(hACSCLibraryModule, "_acsc_EnableResponse@16");												//     32
	acsc_EndSequence = (ACSC_EndSequence) GetProcAddress(hACSCLibraryModule, "_acsc_EndSequence@12");														//     33
	acsc_EndSequenceM = (ACSC_EndSequenceM) GetProcAddress(hACSCLibraryModule, "_acsc_EndSequenceM@12");													//     34
	acsc_ExtAddPoint = (ACSC_ExtAddPoint) GetProcAddress(hACSCLibraryModule, "_acsc_ExtAddPoint@28");														//     35
	acsc_ExtAddPointM = (ACSC_ExtAddPointM) GetProcAddress(hACSCLibraryModule, "_acsc_ExtAddPointM@24");													//     36
	acsc_ExtArc1 = (ACSC_ExtArc1) GetProcAddress(hACSCLibraryModule, "_acsc_ExtArc1@32");																	//     37
	acsc_ExtArc2 = (ACSC_ExtArc2) GetProcAddress(hACSCLibraryModule, "_acsc_ExtArc2@32");																	//     38
	acsc_ExtLine = (ACSC_ExtLine) GetProcAddress(hACSCLibraryModule, "_acsc_ExtLine@24");																	//     39
	acsc_ExtToPoint = (ACSC_ExtToPoint) GetProcAddress(hACSCLibraryModule, "_acsc_ExtToPoint@40");															//     40
	acsc_ExtToPointM = (ACSC_ExtToPointM) GetProcAddress(hACSCLibraryModule, "_acsc_ExtToPointM@36");														//     41
	acsc_GetAcceleration = (ACSC_GetAcceleration) GetProcAddress(hACSCLibraryModule, "_acsc_GetAcceleration@16");											//     42
	acsc_GetAnalogInput = (ACSC_GetAnalogInput) GetProcAddress(hACSCLibraryModule, "_acsc_GetAnalogInput@16");												//     43
	acsc_GetAnalogOutput = (ACSC_GetAnalogOutput) GetProcAddress(hACSCLibraryModule, "_acsc_GetAnalogOutput@16");											//     44
	acsc_GetAxisState = (ACSC_GetAxisState) GetProcAddress(hACSCLibraryModule, "_acsc_GetAxisState@16");													//     45
	acsc_GetCommOptions = (ACSC_GetCommOptions) GetProcAddress(hACSCLibraryModule, "_acsc_GetCommOptions@8");												//     46
	acsc_GetDeceleration = (ACSC_GetDeceleration) GetProcAddress(hACSCLibraryModule, "_acsc_GetDeceleration@16");											//     47
	acsc_GetDefaultTimeout = (ACSC_GetDefaultTimeout) GetProcAddress(hACSCLibraryModule, "_acsc_GetDefaultTimeout@4");										//     48
	acsc_GetErrorString = (ACSC_GetErrorString) GetProcAddress(hACSCLibraryModule, "_acsc_GetErrorString@20");												//     49
	acsc_GetExtInput = (ACSC_GetExtInput) GetProcAddress(hACSCLibraryModule, "_acsc_GetExtInput@20");														//     50
	acsc_GetExtInputPort = (ACSC_GetExtInputPort) GetProcAddress(hACSCLibraryModule, "_acsc_GetExtInputPort@16");											//     51
	acsc_GetExtOutput = (ACSC_GetExtOutput) GetProcAddress(hACSCLibraryModule, "_acsc_GetExtOutput@20");													//     52
	acsc_GetExtOutputPort = (ACSC_GetExtOutputPort) GetProcAddress(hACSCLibraryModule, "_acsc_GetExtOutputPort@16");										//     53
	acsc_GetFPosition = (ACSC_GetFPosition) GetProcAddress(hACSCLibraryModule, "_acsc_GetFPosition@16");													//     54
	acsc_GetFVelocity = (ACSC_GetFVelocity) GetProcAddress(hACSCLibraryModule, "_acsc_GetFVelocity@16");													//     55
	acsc_GetFault = (ACSC_GetFault) GetProcAddress(hACSCLibraryModule, "_acsc_GetFault@16");																//     56
	acsc_GetFaultMask = (ACSC_GetFaultMask) GetProcAddress(hACSCLibraryModule, "_acsc_GetFaultMask@16");													//     57
	acsc_GetFirmwareVersion = (ACSC_GetFirmwareVersion) GetProcAddress(hACSCLibraryModule, "_acsc_GetFirmwareVersion@20");									//     58
	acsc_GetHistory = (ACSC_GetHistory) GetProcAddress(hACSCLibraryModule, "_acsc_GetHistory@20");															//     59
	acsc_GetIndexState = (ACSC_GetIndexState) GetProcAddress(hACSCLibraryModule, "_acsc_GetIndexState@16");													//     60
	acsc_GetInput = (ACSC_GetInput) GetProcAddress(hACSCLibraryModule, "_acsc_GetInput@20");																//     61
	acsc_GetInputPort = (ACSC_GetInputPort) GetProcAddress(hACSCLibraryModule, "_acsc_GetInputPort@16");													//     62
	acsc_GetInterruptMask = (ACSC_GetInterruptMask) GetProcAddress(hACSCLibraryModule, "_acsc_GetInterruptMask@12");										//     63
	acsc_GetJerk = (ACSC_GetJerk) GetProcAddress(hACSCLibraryModule, "_acsc_GetJerk@16");																	//     64
	acsc_GetKillDeceleration = (ACSC_GetKillDeceleration) GetProcAddress(hACSCLibraryModule, "_acsc_GetKillDeceleration@16");								//     65
	acsc_GetLastError = (ACSC_GetLastError) GetProcAddress(hACSCLibraryModule, "_acsc_GetLastError@0");														//     66
	acsc_GetLibraryVersion = (ACSC_GetLibraryVersion) GetProcAddress(hACSCLibraryModule, "_acsc_GetLibraryVersion@0");										//     67
	acsc_GetMessage = (ACSC_GetMessage) GetProcAddress(hACSCLibraryModule, "_acsc_GetMessage@20");															//     68
	acsc_GetMotionError = (ACSC_GetMotionError) GetProcAddress(hACSCLibraryModule, "_acsc_GetMotionError@16");												//     69
	acsc_GetMotorError = (ACSC_GetMotorError) GetProcAddress(hACSCLibraryModule, "_acsc_GetMotorError@16");													//     70
	acsc_GetMotorState = (ACSC_GetMotorState) GetProcAddress(hACSCLibraryModule, "_acsc_GetMotorState@16");													//     71
	acsc_GetOutput = (ACSC_GetOutput) GetProcAddress(hACSCLibraryModule, "_acsc_GetOutput@20");																//     72
	acsc_GetOutputPort = (ACSC_GetOutputPort) GetProcAddress(hACSCLibraryModule, "_acsc_GetOutputPort@16");													//     73
	acsc_GetPCICards = (ACSC_GetPCICards) GetProcAddress(hACSCLibraryModule, "_acsc_GetPCICards@12");														//     74
	acsc_GetEthernetCards = (ACSC_GetEthernetCards) GetProcAddress(hACSCLibraryModule, "_acsc_GetEthernetCards");											//	   247
	acsc_GetProgramError = (ACSC_GetProgramError) GetProcAddress(hACSCLibraryModule, "_acsc_GetProgramError@16");											//     75
	acsc_GetProgramState = (ACSC_GetProgramState) GetProcAddress(hACSCLibraryModule, "_acsc_GetProgramState@16");											//     76
	acsc_GetRPosition = (ACSC_GetRPosition) GetProcAddress(hACSCLibraryModule, "_acsc_GetRPosition@16");													//     77
	acsc_GetRVelocity = (ACSC_GetRVelocity) GetProcAddress(hACSCLibraryModule, "_acsc_GetRVelocity@16");													//     78
	acsc_GetResponseMask = (ACSC_GetResponseMask) GetProcAddress(hACSCLibraryModule, "_acsc_GetResponseMask@16");											//     79
	acsc_GetSafetyInput = (ACSC_GetSafetyInput) GetProcAddress(hACSCLibraryModule, "_acsc_GetSafetyInput@20");												//     80
	acsc_GetSafetyInputPort = (ACSC_GetSafetyInputPort) GetProcAddress(hACSCLibraryModule, "_acsc_GetSafetyInputPort@16");									//     81
	acsc_GetSafetyInputPortInv = (ACSC_GetSafetyInputPortInv) GetProcAddress(hACSCLibraryModule, "_acsc_GetSafetyInputPortInv@16");							//     82
	acsc_GetSerialNumber = (ACSC_GetSerialNumber) GetProcAddress(hACSCLibraryModule, "_acsc_GetSerialNumber@20");											//     83
	acsc_GetTimeout = (ACSC_GetTimeout) GetProcAddress(hACSCLibraryModule, "_acsc_GetTimeout@4");															//     84
	acsc_GetVelocity = (ACSC_GetVelocity) GetProcAddress(hACSCLibraryModule, "_acsc_GetVelocity@16");														//     85
	acsc_Go = (ACSC_Go) GetProcAddress(hACSCLibraryModule, "_acsc_Go@12");																					//     86
	acsc_GoM = (ACSC_GoM) GetProcAddress(hACSCLibraryModule, "_acsc_GoM@12");																				//     87
	acsc_Group = (ACSC_Group) GetProcAddress(hACSCLibraryModule, "_acsc_Group@12");																			//     88
	acsc_Halt = (ACSC_Halt) GetProcAddress(hACSCLibraryModule, "_acsc_Halt@12");																			//     89
	acsc_HaltM = (ACSC_HaltM) GetProcAddress(hACSCLibraryModule, "_acsc_HaltM@12");																			//     90
	acsc_Jog = (ACSC_Jog) GetProcAddress(hACSCLibraryModule, "_acsc_Jog@24");																				//     91
	acsc_JogM = (ACSC_JogM) GetProcAddress(hACSCLibraryModule, "_acsc_JogM@28");																			//     92
	acsc_Kill = (ACSC_Kill) GetProcAddress(hACSCLibraryModule, "_acsc_Kill@12");																			//     93
	acsc_KillExt = (ACSC_KillExt) GetProcAddress(hACSCLibraryModule, "_acsc_KillExt@16");																	//     
	acsc_DisableExt = (ACSC_DisableExt) GetProcAddress(hACSCLibraryModule, "_acsc_DisableExt@16");															//     
	acsc_KillAll = (ACSC_KillAll) GetProcAddress(hACSCLibraryModule, "_acsc_KillAll@8");																	//     94
	acsc_KillM = (ACSC_KillM) GetProcAddress(hACSCLibraryModule, "_acsc_KillM@12");																			//     95
	acsc_Line = (ACSC_Line) GetProcAddress(hACSCLibraryModule, "_acsc_Line@16");																			//     96
	acsc_LoadBuffer = (ACSC_LoadBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_LoadBuffer@20");															//     97
	acsc_MultiPoint = (ACSC_MultiPoint) GetProcAddress(hACSCLibraryModule, "_acsc_MultiPoint@24");															//     98
	acsc_MultiPointM = (ACSC_MultiPointM) GetProcAddress(hACSCLibraryModule, "_acsc_MultiPointM@24");														//     99
#if defined(WIN32) && !defined(UNDER_RTSS)
	acsc_OpenCommDirect = (ACSC_OpenCommDirect) GetProcAddress(hACSCLibraryModule, "_acsc_OpenCommDirect@0");
	acsc_OpenCommSimulator = (ACSC_OpenCommSimulator) GetProcAddress(hACSCLibraryModule, "_acsc_OpenCommSimulator@4");										// 
	acsc_CloseSimulator	=	(ACSC_CloseSimulator) GetProcAddress(hACSCLibraryModule, "_acsc_CloseSimulator@0");												//
	acsc_OpenCommEthernet = (ACSC_OpenCommEthernet) GetProcAddress(hACSCLibraryModule, "_acsc_OpenCommEthernet@8");											//     101
	acsc_OpenCommSerial = (ACSC_OpenCommSerial) GetProcAddress(hACSCLibraryModule, "_acsc_OpenCommSerial@8");												//     103
#endif
	acsc_OpenCommPCI = (ACSC_OpenCommPCI) GetProcAddress(hACSCLibraryModule, "_acsc_OpenCommPCI@4");														//     102
	acsc_OpenHistoryBuffer = (ACSC_OpenHistoryBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_OpenHistoryBuffer@8");										//     104
	acsc_OpenLogFile = (ACSC_OpenLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_OpenLogFile@8");														//     105
	acsc_OpenMessageBuffer = (ACSC_OpenMessageBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_OpenMessageBuffer@8");										//     106
	acsc_Projection = (ACSC_Projection) GetProcAddress(hACSCLibraryModule, "_acsc_Projection@16");															//     107
	acsc_ReadDPRAMInteger = (ACSC_ReadDPRAMInteger) GetProcAddress(hACSCLibraryModule, "_acsc_ReadDPRAMInteger@12");										//     108
	acsc_ReadDPRAMReal = (ACSC_ReadDPRAMReal) GetProcAddress(hACSCLibraryModule, "_acsc_ReadDPRAMReal@12");													//     109
	acsc_ReadInteger = (ACSC_ReadInteger) GetProcAddress(hACSCLibraryModule, "_acsc_ReadInteger@36");														//     110
	acsc_ReadReal = (ACSC_ReadReal) GetProcAddress(hACSCLibraryModule, "_acsc_ReadReal@36");																//     111
	acsc_Receive = (ACSC_Receive) GetProcAddress(hACSCLibraryModule, "_acsc_Receive@20");																	//     112
	acsc_ReleaseComm = (ACSC_ReleaseComm) GetProcAddress(hACSCLibraryModule, "_acsc_ReleaseComm@4");														//     113
	acsc_ResetIndexState = (ACSC_ResetIndexState) GetProcAddress(hACSCLibraryModule, "_acsc_ResetIndexState@16");											//     114
	acsc_RunBuffer = (ACSC_RunBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_RunBuffer@16");																//     115
	acsc_Segment = (ACSC_Segment) GetProcAddress(hACSCLibraryModule, "_acsc_Segment@20");																	//     116
	acsc_Send = (ACSC_Send) GetProcAddress(hACSCLibraryModule, "_acsc_Send@16");																			//     117
	acsc_SetAcceleration = (ACSC_SetAcceleration) GetProcAddress(hACSCLibraryModule, "_acsc_SetAcceleration@20");											//     118
	acsc_SetAccelerationImm = (ACSC_SetAccelerationImm) GetProcAddress(hACSCLibraryModule, "_acsc_SetAccelerationImm@20");									//     119
	acsc_SetAnalogOutput = (ACSC_SetAnalogOutput) GetProcAddress(hACSCLibraryModule, "_acsc_SetAnalogOutput@16");											//     120
	acsc_SetCallback = (ACSC_SetCallback) GetProcAddress(hACSCLibraryModule, "_acsc_SetCallback@12");														//     121
	acsc_SetCallbackPriority = (ACSC_SetCallbackPriority) GetProcAddress(hACSCLibraryModule, "_acsc_SetCallbackPriority@8");								//     122
	acsc_SetCommOptions = (ACSC_SetCommOptions) GetProcAddress(hACSCLibraryModule, "_acsc_SetCommOptions@8");												//     123
	acsc_SetDeceleration = (ACSC_SetDeceleration) GetProcAddress(hACSCLibraryModule, "_acsc_SetDeceleration@20");											//     124
	acsc_SetDecelerationImm = (ACSC_SetDecelerationImm) GetProcAddress(hACSCLibraryModule, "_acsc_SetDecelerationImm@20");									//     125
	acsc_SetExtOutput = (ACSC_SetExtOutput) GetProcAddress(hACSCLibraryModule, "_acsc_SetExtOutput@20");													//     126
	acsc_SetExtOutputPort = (ACSC_SetExtOutputPort) GetProcAddress(hACSCLibraryModule, "_acsc_SetExtOutputPort@16");										//     127
	acsc_SetFPosition = (ACSC_SetFPosition) GetProcAddress(hACSCLibraryModule, "_acsc_SetFPosition@20");													//     128
	acsc_SetFaultMask = (ACSC_SetFaultMask) GetProcAddress(hACSCLibraryModule, "_acsc_SetFaultMask@16");													//     129
	acsc_SetInterruptMask = (ACSC_SetInterruptMask) GetProcAddress(hACSCLibraryModule, "_acsc_SetInterruptMask@12");										//     130
	acsc_SetIterations = (ACSC_SetIterations) GetProcAddress(hACSCLibraryModule, "_acsc_SetIterations@8");													//     131
	acsc_SetJerk = (ACSC_SetJerk) GetProcAddress(hACSCLibraryModule, "_acsc_SetJerk@20");																	//     132
	acsc_SetJerkImm = (ACSC_SetJerkImm) GetProcAddress(hACSCLibraryModule, "_acsc_SetJerkImm@20");															//     133
	acsc_SetKillDeceleration = (ACSC_SetKillDeceleration) GetProcAddress(hACSCLibraryModule, "_acsc_SetKillDeceleration@20");								//     134
	acsc_SetKillDecelerationImm = (ACSC_SetKillDecelerationImm) GetProcAddress(hACSCLibraryModule, "_acsc_SetKillDecelerationImm@20");						//     135
	acsc_SetMaster = (ACSC_SetMaster) GetProcAddress(hACSCLibraryModule, "_acsc_SetMaster@16");																//     136
	acsc_SetOutput = (ACSC_SetOutput) GetProcAddress(hACSCLibraryModule, "_acsc_SetOutput@20");																//     137
	acsc_SetOutputPort = (ACSC_SetOutputPort) GetProcAddress(hACSCLibraryModule, "_acsc_SetOutputPort@16");													//     138
	acsc_SetRPosition = (ACSC_SetRPosition) GetProcAddress(hACSCLibraryModule, "_acsc_SetRPosition@20");													//     139
	acsc_SetResponseMask = (ACSC_SetResponseMask) GetProcAddress(hACSCLibraryModule, "_acsc_SetResponseMask@16");											//     140
	acsc_SetSafetyInputPortInv = (ACSC_SetSafetyInputPortInv) GetProcAddress(hACSCLibraryModule, "_acsc_SetSafetyInputPortInv@16");							//     141
	acsc_SetTimeout = (ACSC_SetTimeout) GetProcAddress(hACSCLibraryModule, "_acsc_SetTimeout@8");															//     142
	acsc_SetVelocity = (ACSC_SetVelocity) GetProcAddress(hACSCLibraryModule, "_acsc_SetVelocity@20");														//     143
	acsc_SetVelocityImm = (ACSC_SetVelocityImm) GetProcAddress(hACSCLibraryModule, "_acsc_SetVelocityImm@20");												//     144
	acsc_Slave = (ACSC_Slave) GetProcAddress(hACSCLibraryModule, "_acsc_Slave@16");																			//     145
	acsc_SlaveStalled = (ACSC_SlaveStalled) GetProcAddress(hACSCLibraryModule, "_acsc_SlaveStalled@32");													//     146
	acsc_Spline = (ACSC_Spline) GetProcAddress(hACSCLibraryModule, "_acsc_Spline@24");																		//     147
	acsc_SplineM = (ACSC_SplineM) GetProcAddress(hACSCLibraryModule, "_acsc_SplineM@24");																	//     148
	acsc_Split = (ACSC_Split) GetProcAddress(hACSCLibraryModule, "_acsc_Split@12");																			//     149
	acsc_SplitAll = (ACSC_SplitAll) GetProcAddress(hACSCLibraryModule, "_acsc_SplitAll@8");																	//     150
	acsc_StopBuffer = (ACSC_StopBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_StopBuffer@12");															//     151
	acsc_StopCollect = (ACSC_StopCollect) GetProcAddress(hACSCLibraryModule, "_acsc_StopCollect@8");														//     152
	acsc_Stopper = (ACSC_Stopper) GetProcAddress(hACSCLibraryModule, "_acsc_Stopper@12");																	//     153
	acsc_SuspendBuffer = (ACSC_SuspendBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_SuspendBuffer@12");													//     154
	acsc_ToPoint = (ACSC_ToPoint) GetProcAddress(hACSCLibraryModule, "_acsc_ToPoint@24");																	//     155
	acsc_ToPointM = (ACSC_ToPointM) GetProcAddress(hACSCLibraryModule, "_acsc_ToPointM@20");																//     156
	acsc_Transaction = (ACSC_Transaction) GetProcAddress(hACSCLibraryModule, "_acsc_Transaction@28");														//     157
	acsc_UploadBuffer = (ACSC_UploadBuffer) GetProcAddress(hACSCLibraryModule, "_acsc_UploadBuffer@28");													//     158
	acsc_WaitCollectEnd = (ACSC_WaitCollectEnd) GetProcAddress(hACSCLibraryModule, "_acsc_WaitCollectEnd@8");												//     159
	acsc_WaitForAsyncCall = (ACSC_WaitForAsyncCall) GetProcAddress(hACSCLibraryModule, "_acsc_WaitForAsyncCall@20");										//     160
	acsc_WaitInput = (ACSC_WaitInput) GetProcAddress(hACSCLibraryModule, "_acsc_WaitInput@20");																//     161
	acsc_WaitLogicalMotionEnd = (ACSC_WaitLogicalMotionEnd) GetProcAddress(hACSCLibraryModule, "_acsc_WaitLogicalMotionEnd@12");							//     162
	acsc_WaitMotionEnd = (ACSC_WaitMotionEnd) GetProcAddress(hACSCLibraryModule, "_acsc_WaitMotionEnd@12");													//     163
	acsc_WaitMotorEnabled = (ACSC_WaitMotorEnabled) GetProcAddress(hACSCLibraryModule, "_acsc_WaitMotorEnabled@16");										//     164
	acsc_WaitProgramEnd = (ACSC_WaitProgramEnd) GetProcAddress(hACSCLibraryModule, "_acsc_WaitProgramEnd@12");												//     165
	acsc_WaitUserCondition = (ACSC_WaitUserCondition) GetProcAddress(hACSCLibraryModule, "_acsc_WaitUserCondition@12");										//     166
	acsc_WriteDPRAMInteger = (ACSC_WriteDPRAMInteger) GetProcAddress(hACSCLibraryModule, "_acsc_WriteDPRAMInteger@12");										//     167
	acsc_WriteDPRAMReal = (ACSC_WriteDPRAMReal) GetProcAddress(hACSCLibraryModule, "_acsc_WriteDPRAMReal@16");												//     168
	acsc_WriteInteger = (ACSC_WriteInteger) GetProcAddress(hACSCLibraryModule, "_acsc_WriteInteger@36");													//     169
	acsc_WriteLogFile = (ACSC_WriteLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_WriteLogFile@12");													//     170
	acsc_WriteReal = (ACSC_WriteReal) GetProcAddress(hACSCLibraryModule, "_acsc_WriteReal@36");																//     171
	acsc_LoadBufferIgnoreServiceLines = (ACSC_LoadBufferIgnoreServiceLines) GetProcAddress(hACSCLibraryModule, "_acsc_LoadBufferIgnoreServiceLines@20");	//     196
	acsc_PegI = (ACSC_PegI) GetProcAddress(hACSCLibraryModule, "_acsc_PegI@48");																			//     197
	acsc_PegR = (ACSC_PegR) GetProcAddress(hACSCLibraryModule, "_acsc_PegR@44");																			//     198
	acsc_AssignPins = (ACSC_AssignPins) GetProcAddress(hACSCLibraryModule, "_acsc_AssignPins@16");															//	   199
	acsc_StopPeg = (ACSC_StopPeg) GetProcAddress(hACSCLibraryModule, "_acsc_StopPeg@12");																	//	   200
	acsc_CollectB = (ACSC_CollectB) GetProcAddress(hACSCLibraryModule, "_acsc_CollectB@28");																//     201
	acsc_DataCollection = (ACSC_DataCollection) GetProcAddress(hACSCLibraryModule, "_acsc_DataCollection@32");												//     249
	acsc_AddPVPoint = (ACSC_AddPVPoint) GetProcAddress(hACSCLibraryModule, "_acsc_AddPVPoint@28");															//     202
	acsc_AddPVPointM = (ACSC_AddPVPointM) GetProcAddress(hACSCLibraryModule, "_acsc_AddPVPointM@20");														//     203
	acsc_AddPVTPoint = (ACSC_AddPVTPoint) GetProcAddress(hACSCLibraryModule, "_acsc_AddPVTPoint@36");														//     204
	acsc_AddPVTPointM = (ACSC_AddPVTPointM) GetProcAddress(hACSCLibraryModule, "_acsc_AddPVTPointM@28");													//     205
	acsc_LoadFileToRealVariable = (ACSC_LoadFileToRealVariable) GetProcAddress(hACSCLibraryModule, "_acsc_LoadFileToRealVariable@36");						//     206
	acsc_LoadFileToIntegerVariable = (ACSC_LoadFileToIntegerVariable) GetProcAddress(hACSCLibraryModule, "_acsc_LoadFileToIntegerVariable@36");				//     207
    acsc_LoadDataToController = (ACSC_LoadDataToController) GetProcAddress(hACSCLibraryModule, "_acsc_LoadDataToController@44");							//     250
    acsc_UploadDataFromController = (ACSC_UploadDataFromController) GetProcAddress(hACSCLibraryModule, "_acsc_UploadDataFromController@48");				//     253
	acsc_SetQueueOverflowTimeout = (ACSC_SetQueueOverflowTimeout) GetProcAddress(hACSCLibraryModule, "_acsc_SetQueueOverflowTimeout@8");					//     208
	acsc_GetQueueOverflowTimeout = (ACSC_GetQueueOverflowTimeout) GetProcAddress(hACSCLibraryModule, "_acsc_GetQueueOverflowTimeout@4");					//     209
	acsc_LoadBuffersFromFile = (ACSC_LoadBuffersFromFile) GetProcAddress(hACSCLibraryModule, "_acsc_LoadBuffersFromFile@12");								//     210
	acsc_SetTargetPosition = (ACSC_SetTargetPosition) GetProcAddress(hACSCLibraryModule, "_acsc_SetTargetPosition@20");										//     211
	acsc_GetTargetPosition = (ACSC_GetTargetPosition) GetProcAddress(hACSCLibraryModule, "_acsc_GetTargetPosition@16");										//     212
	acsc_SetTargetPositionM = (ACSC_SetTargetPositionM) GetProcAddress(hACSCLibraryModule, "_acsc_SetTargetPositionM@16");									//     213
	acsc_Track = (ACSC_Track) GetProcAddress(hACSCLibraryModule, "_acsc_Track@16");																			//     214
	acsc_TrackM = (ACSC_TrackM) GetProcAddress(hACSCLibraryModule, "_acsc_TrackM@16");																		//     215
	acsc_FaultClearM = (ACSC_FaultClearM) GetProcAddress(hACSCLibraryModule, "_acsc_FaultClearM@12");														//     216
	acsc_FaultClear = (ACSC_FaultClear) GetProcAddress(hACSCLibraryModule, "_acsc_FaultClear@12");															//     217
	acsc_Getconf = (ACSC_Getconf) GetProcAddress(hACSCLibraryModule, "_acsc_Getconf@20");																	//     218
	acsc_Setconf = (ACSC_Setconf) GetProcAddress(hACSCLibraryModule, "_acsc_Setconf@20");																	//     219
	acsc_SetCallbackExt = (ACSC_SetCallbackExt) GetProcAddress(hACSCLibraryModule, "_acsc_SetCallbackExt@16");												//	   222
	acsc_DownloadBinVariableToFile = (ACSC_DownloadBinVariableToFile) GetProcAddress(hACSCLibraryModule, "_acsc_DownloadBinVariableToFile@44");				//     223
	acsc_SetLogFileOptions = (ACSC_SetLogFileOptions)GetProcAddress(hACSCLibraryModule, "_acsc_SetLogFileOptions@12");										//	   224

	acsc_GetConf=(ACSC_GetConf)GetProcAddress(hACSCLibraryModule, "_acsc_GetConf@20");																		//	   228
	acsc_SetConf=(ACSC_SetConf)GetProcAddress(hACSCLibraryModule, "_acsc_SetConf@24");																		//	   229
	acsc_SetServer=(ACSC_SetServer)GetProcAddress(hACSCLibraryModule, "_acsc_SetServer@4");																	//	   230
	acsc_GetSingleMessage=(ACSC_GetSingleMessage)GetProcAddress(hACSCLibraryModule, "_acsc_GetSingleMessage@20");											//	   231

	acsc_GetCallbackMask = (ACSC_GetCallbackMask) GetProcAddress(hACSCLibraryModule, "_acsc_GetCallbackMask@12");											//     232
	acsc_SetCallbackMask = (ACSC_SetCallbackMask) GetProcAddress(hACSCLibraryModule, "_acsc_SetCallbackMask@16");											//     233
	acsc_InstallCallback = (ACSC_InstallCallback) GetProcAddress(hACSCLibraryModule, "_acsc_InstallCallback@16");											//	   234
	acsc_PegInc = (ACSC_PegInc) GetProcAddress(hACSCLibraryModule, "_acsc_PegInc@60");																		//     235
	acsc_PegRandom = (ACSC_PegRandom) GetProcAddress(hACSCLibraryModule, "_acsc_PegRandom@44");																//     236
	acsc_Commut = (ACSC_Commut) GetProcAddress(hACSCLibraryModule, "_acsc_Commut@12");																		//     237
	acsc_WaitMotorCommutated = (ACSC_WaitMotorCommutated) GetProcAddress(hACSCLibraryModule, "_acsc_WaitMotorCommutated@16");								//     238
    acsc_GetConnectionsList	= (ACSC_GetConnectionsList)	GetProcAddress(hACSCLibraryModule,"_acsc_GetConnectionsList@12");									//     245
    acsc_TerminateConnection = (ACSC_TerminateConnection) GetProcAddress(hACSCLibraryModule,"_acsc_TerminateConnection@4");									//     246
    acsc_SetServerExt = (ACSC_SetServerExt) GetProcAddress(hACSCLibraryModule,"_acsc_SetServerExt@8");														//     247
    acsc_SetServerExtLogin = (ACSC_SetServerExtLogin) GetProcAddress(hACSCLibraryModule,"_acsc_SetServerExtLogin@20");										//     248
    acsc_RegisterEmergencyStop = (ACSC_RegisterEmergencyStop) GetProcAddress(hACSCLibraryModule,"_acsc_RegisterEmergencyStop@0");							//     251
	acsc_UnregisterEmergencyStop = (ACSC_UnregisterEmergencyStop) GetProcAddress(hACSCLibraryModule,"_acsc_UnregisterEmergencyStop@0");						//     252
	acsc_GetUMDVersion = (ACSC_GetUMDVersion)GetProcAddress(hACSCLibraryModule,"_acsc_GetUMDVersion@0");													//	   258
	acsc_AnalyzeApplication	= (ACSC_AnalyzeApplication) GetProcAddress(hACSCLibraryModule,"_acsc_AnalyzeApplication@16");									//     254
	acsc_FreeApplication = (ACSC_FreeApplication) GetProcAddress(hACSCLibraryModule,"_acsc_FreeApplication@4");												//     255
	acsc_SaveApplication = (ACSC_SaveApplication) GetProcAddress(hACSCLibraryModule,"_acsc_SaveApplication@16");											//     256
	acsc_LoadApplication = (ACSC_LoadApplication) GetProcAddress(hACSCLibraryModule,"_acsc_LoadApplication@16");											//     257
	acsc_OpenCommEthernetTCP = (ACSC_OpenCommEthernetTCP) GetProcAddress(hACSCLibraryModule, "_acsc_OpenCommEthernetTCP@8");								//     259
	acsc_OpenCommEthernetUDP = (ACSC_OpenCommEthernetUDP) GetProcAddress(hACSCLibraryModule, "_acsc_OpenCommEthernetUDP@8");								//     260
	acsc_ControllerReboot = (ACSC_ControllerReboot) GetProcAddress(hACSCLibraryModule, "_acsc_ControllerReboot@8");											//     262
	acsc_ControllerFactoryDefault=(ACSC_ControllerFactoryDefault)GetProcAddress(hACSCLibraryModule,"_acsc_ControllerFactoryDefault@8");						//     263

	acsc_GetSharedMemoryAddress = (ACSC_GetSharedMemoryAddress)GetProcAddress(hACSCLibraryModule,"_acsc_GetSharedMemoryAddress@20");						//     264
	acsc_ReadSharedMemoryReal = (ACSC_ReadSharedMemoryReal)GetProcAddress(hACSCLibraryModule,"_acsc_ReadSharedMemoryReal@28");								//     265
	acsc_ReadSharedMemoryInteger = (ACSC_ReadSharedMemoryInteger)GetProcAddress(hACSCLibraryModule,"_acsc_ReadSharedMemoryInteger@28");						//     266
	acsc_WriteSharedMemoryReal = (ACSC_WriteSharedMemoryReal)GetProcAddress(hACSCLibraryModule,"_acsc_WriteSharedMemoryReal@28");							//     267
	acsc_WriteSharedMemoryInteger = (ACSC_WriteSharedMemoryInteger)GetProcAddress(hACSCLibraryModule,"_acsc_WriteSharedMemoryInteger@28");					//     268

	acsc_SysInfo = (ACSC_SysInfo)GetProcAddress(hACSCLibraryModule, "_acsc_SysInfo@16");																	//	   269

	acsc_GetAxesCount = (ACSC_GetAxesCount)GetProcAddress(hACSCLibraryModule, "_acsc_GetAxesCount@12");														//	   270
	acsc_GetBuffersCount = (ACSC_GetBuffersCount)GetProcAddress(hACSCLibraryModule, "_acsc_GetBuffersCount@12");											//	   271
	acsc_GetDBufferIndex = (ACSC_GetDBufferIndex)GetProcAddress(hACSCLibraryModule, "_acsc_GetDBufferIndex@12");											//	   272

	acsc_AssignPegNT = (ACSC_AssignPegNT)GetProcAddress(hACSCLibraryModule, "_acsc_AssignPegNT@20");														//	   273
	acsc_AssignPegOutputsNT = (ACSC_AssignPegOutputsNT)GetProcAddress(hACSCLibraryModule, "_acsc_AssignPegOutputsNT@20");									//	   274
	acsc_AssignFastInputsNT = (ACSC_AssignFastInputsNT)GetProcAddress(hACSCLibraryModule, "_acsc_AssignFastInputsNT@20");									//	   275
	acsc_PegIncNT = (ACSC_PegIncNT)GetProcAddress(hACSCLibraryModule, "_acsc_PegIncNT@60");																	//	   276
	acsc_PegRandomNT = (ACSC_PegRandomNT)GetProcAddress(hACSCLibraryModule, "_acsc_PegRandomNT@56");														//	   277
	acsc_WaitPegReadyNT = (ACSC_WaitPegReadyNT)GetProcAddress(hACSCLibraryModule, "_acsc_WaitPegReadyNT@12");												//	   278
	acsc_StartPegNT = (ACSC_StartPegNT)GetProcAddress(hACSCLibraryModule, "_acsc_StartPegNT@12");															//	   279
	acsc_StopPegNT = (ACSC_StopPegNT)GetProcAddress(hACSCLibraryModule, "_acsc_StopPegNT@12");																//	   280
	
	acsc_GetEtherCATState = (ACSC_GetEtherCATState)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATState@12");											//     281
	acsc_GetEtherCATError = (ACSC_GetEtherCATError)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATError@12");											//     282
	acsc_MapEtherCATInput = (ACSC_MapEtherCATInput)GetProcAddress(hACSCLibraryModule,"_acsc_MapEtherCATInput@20");											//     283
	acsc_MapEtherCATOutput = (ACSC_MapEtherCATOutput)GetProcAddress(hACSCLibraryModule,"_acsc_MapEtherCATOutput@20");										//     284
	acsc_UnmapEtherCATInputsOutputs	= (ACSC_UnmapEtherCATInputsOutputs)GetProcAddress(hACSCLibraryModule,"_acsc_UnmapEtherCATInputsOutputs@8");				//     285
	acsc_GetEtherCATSlaveIndex = (ACSC_GetEtherCATSlaveIndex)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATSlaveIndex@24");							//     286
	acsc_GetEtherCATSlaveOffset = (ACSC_GetEtherCATSlaveOffset)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATSlaveOffset@20");						//     287
	acsc_GetEtherCATSlaveVendorID = (ACSC_GetEtherCATSlaveVendorID)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATSlaveVendorID@16");					//     288
	acsc_GetEtherCATSlaveProductID = (ACSC_GetEtherCATSlaveProductID)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATSlaveProductID@16");				//     289
	acsc_GetEtherCATSlaveRevision = (ACSC_GetEtherCATSlaveRevision)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATSlaveRevision@16");					//     290
	acsc_GetEtherCATSlaveType = (ACSC_GetEtherCATSlaveType)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATSlaveType@20");								//     291
	acsc_GetEtherCATSlaveState = (ACSC_GetEtherCATSlaveState)GetProcAddress(hACSCLibraryModule,"_acsc_GetEtherCATSlaveState@16");							//     292
	acsc_DownloadFileOverEtherCAT = (ACSC_DownloadFileOverEtherCAT)GetProcAddress(hACSCLibraryModule,"_acsc_DownloadFileOverEtherCAT@20");					//     293
	acsc_ReadSDOValueOverEtherCAT = (ACSC_ReadSDOValueOverEtherCAT)GetProcAddress(hACSCLibraryModule,"_acsc_ReadSDOValueOverEtherCAT@28");					//     294
	acsc_WriteSDOValueOverEtherCAT = (ACSC_WriteSDOValueOverEtherCAT)GetProcAddress(hACSCLibraryModule,"_acsc_WriteSDOValueOverEtherCAT@32");				//     295

	acsc_GetConnectionInfo = (ACSC_GetConnectionInfo)GetProcAddress(hACSCLibraryModule,"_acsc_GetConnectionInfo@8");										//     296
	acsc_GetLogData = (ACSC_GetLogData)GetProcAddress(hACSCLibraryModule,"_acsc_GetLogData@20");															//     297

	acsc_OpenSCLogFile = (ACSC_OpenSCLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_OpenSCLogFile@8");													//     298
	acsc_CloseSCLogFile = (ACSC_CloseSCLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_CloseSCLogFile@4");												//     299
	acsc_WriteSCLogFile = (ACSC_WriteSCLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_WriteSCLogFile@12");												//     300
	acsc_FlushSCLogFile = (ACSC_FlushSCLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_FlushSCLogFile@8");												//     301
	acsc_FlushLogFile = (ACSC_FlushLogFile) GetProcAddress(hACSCLibraryModule, "_acsc_FlushLogFile@4");														//     302

	acsc_DataCollectionExt = (ACSC_DataCollectionExt) GetProcAddress(hACSCLibraryModule, "_acsc_DataCollectionExt@36");										//     303

	acsc_CopyFileToController = (ACSC_CopyFileToController) GetProcAddress(hACSCLibraryModule, "_acsc_CopyFileToController@16");							//     304

	acsc_SegmentedMotion = (ACSC_SegmentedMotion) GetProcAddress(hACSCLibraryModule, "_acsc_SegmentedMotion@20");											//     305
	acsc_ExtendedSegmentedMotion = (ACSC_ExtendedSegmentedMotion) GetProcAddress(hACSCLibraryModule, "_acsc_ExtendedSegmentedMotion@64");					//     306
	acsc_SegmentLine = (ACSC_SegmentLine) GetProcAddress(hACSCLibraryModule, "_acsc_SegmentLine@52");														//     307
	acsc_SegmentArc1 = (ACSC_SegmentArc1) GetProcAddress(hACSCLibraryModule, "_acsc_SegmentArc1@60");														//	   308
	acsc_SegmentArc2 = (ACSC_SegmentArc2) GetProcAddress(hACSCLibraryModule, "_acsc_SegmentArc2@60");														//	   309

	acsc_GetAnalogInputNT = (ACSC_GetAnalogInputNT) GetProcAddress(hACSCLibraryModule, "_acsc_GetAnalogInputNT@16");										//     310
	acsc_GetAnalogOutputNT = (ACSC_GetAnalogOutputNT) GetProcAddress(hACSCLibraryModule, "_acsc_GetAnalogOutputNT@16");										//     311
	acsc_SetAnalogOutputNT = (ACSC_SetAnalogOutputNT) GetProcAddress(hACSCLibraryModule, "_acsc_SetAnalogOutputNT@20");										//     312

	acsc_GetVolatileMemoryUsage = (ACSC_GetVolatileMemoryUsage) GetProcAddress(hACSCLibraryModule, "_acsc_GetVolatileMemoryUsage@12");						//     313
	acsc_GetVolatileMemoryTotal = (ACSC_GetVolatileMemoryTotal) GetProcAddress(hACSCLibraryModule, "_acsc_GetVolatileMemoryTotal@12");						//     314
	acsc_GetVolatileMemoryFree = (ACSC_GetVolatileMemoryFree) GetProcAddress(hACSCLibraryModule, "_acsc_GetVolatileMemoryFree@12");							//     315
	acsc_GetNonVolatileMemoryUsage = (ACSC_GetNonVolatileMemoryUsage) GetProcAddress(hACSCLibraryModule, "_acsc_GetNonVolatileMemoryUsage@12");				//     316
	acsc_GetNonVolatileMemoryTotal = (ACSC_GetNonVolatileMemoryTotal) GetProcAddress(hACSCLibraryModule, "_acsc_GetNonVolatileMemoryTotal@12");				//     317
	acsc_GetNonVolatileMemoryFree = (ACSC_GetNonVolatileMemoryFree) GetProcAddress(hACSCLibraryModule, "_acsc_GetNonVolatileMemoryFree@12");				//     318

	acsc_DeleteFileFromController = (ACSC_DeleteFileFromController) GetProcAddress(hACSCLibraryModule, "_acsc_DeleteFileFromController@12");				//     319

	acsc_ControllerSaveToFlash = (ACSC_ControllerSaveToFlash)GetProcAddress(hACSCLibraryModule,"_acsc_ControllerSaveToFlash@20");							//     320

	acsc_StartSPiiPlusSC = (ACSC_StartSPiiPlusSC) GetProcAddress(hACSCLibraryModule, "_acsc_StartSPiiPlusSC@0");											//     321
	acsc_StopSPiiPlusSC = (ACSC_StopSPiiPlusSC) GetProcAddress(hACSCLibraryModule, "_acsc_StopSPiiPlusSC@0");												//     322

	acsc_WaitCollectEndExt = (ACSC_WaitCollectEndExt) GetProcAddress(hACSCLibraryModule, "_acsc_WaitCollectEndExt@12");										//	   323
	acsc_CommutExt = (ACSC_CommutExt) GetProcAddress(hACSCLibraryModule, "_acsc_CommutExt@28");																//     324

	acsc_SegmentLineExt = (ACSC_SegmentLineExt) GetProcAddress(hACSCLibraryModule, "_acsc_SegmentLine@56");													//     324
	acsc_SegmentArc1Ext = (ACSC_SegmentArc1Ext) GetProcAddress(hACSCLibraryModule, "_acsc_SegmentArc1@64");													//	   325
	acsc_SegmentArc2Ext = (ACSC_SegmentArc2Ext) GetProcAddress(hACSCLibraryModule, "_acsc_SegmentArc2@64");													//	   326
	acsc_ExtendedSegmentedMotionExt = (ACSC_ExtendedSegmentedMotionExt) GetProcAddress(hACSCLibraryModule, "_acsc_ExtendedSegmentedMotion@76");				//     327
	acsc_BlendedSegmentMotion = (ACSC_BlendedSegmentMotion) GetProcAddress(hACSCLibraryModule, "_acsc_BlendedSegmentMotion@56");							//		328
	acsc_BlendedLine = (ACSC_BlendedLine) GetProcAddress(hACSCLibraryModule, "_acsc_BlendedLine@52");														//		329
	acsc_BlendedArc1 = (ACSC_BlendedArc1) GetProcAddress(hACSCLibraryModule, "_acsc_BlendedArc1@60");														//		330
	acsc_BlendedArc2 = (ACSC_BlendedArc2) GetProcAddress(hACSCLibraryModule, "_acsc_BlendedArc2@60");														//		331

	return 1;
}

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function unmapps from the address space of the calling process.
//////////////////////////////////////////////////////////////////////////////////////////////////
static int FreeACSCLibrary()
{
	return FreeLibrary(hACSCLibraryModule);
}

#else // defined (ACSC_RUNTIME_DYNAMIC_VARIABLES)

extern ACSC_AddMPoint						acsc_AddMPoint;
extern ACSC_AddMPointM						acsc_AddMPointM;
extern ACSC_AddPoint						acsc_AddPoint;
extern ACSC_AddPointM						acsc_AddPointM;
extern ACSC_AppendBuffer					acsc_AppendBuffer;
extern ACSC_Arc1							acsc_Arc1;
extern ACSC_Arc2							acsc_Arc2;
extern ACSC_Break							acsc_Break;
extern ACSC_BreakM							acsc_BreakM;
extern ACSC_CancelOperation					acsc_CancelOperation;
extern ACSC_CaptureComm						acsc_CaptureComm;
extern ACSC_ClearBuffer						acsc_ClearBuffer;
extern ACSC_ClearVariables					acsc_ClearVariables;
extern ACSC_CloseComm						acsc_CloseComm;
extern ACSC_CloseHistoryBuffer				acsc_CloseHistoryBuffer;
extern ACSC_CloseLogFile					acsc_CloseLogFile;
extern ACSC_CloseSCLogFile					acsc_CloseSCLogFile;
extern ACSC_CloseMessageBuffer				acsc_CloseMessageBuffer;
extern ACSC_Collect							acsc_Collect;
extern ACSC_Command							acsc_Command;
extern ACSC_Commut							acsc_Commut;
extern ACSC_CommutExt						acsc_CommutExt;
extern ACSC_CompileBuffer					acsc_CompileBuffer;
extern ACSC_DeclareVariable					acsc_DeclareVariable;
extern ACSC_Disable							acsc_Disable;
extern ACSC_DisableAll						acsc_DisableAll;
extern ACSC_DisableFault					acsc_DisableFault;
extern ACSC_DisableM						acsc_DisableM;
extern ACSC_DisableResponse					acsc_DisableResponse;
extern ACSC_DownloadBuffer					acsc_DownloadBuffer;
extern ACSC_Enable							acsc_Enable;
extern ACSC_EnableFault						acsc_EnableFault;
extern ACSC_EnableM							acsc_EnableM;
extern ACSC_EnableResponse					acsc_EnableResponse;
extern ACSC_EndSequence						acsc_EndSequence;
extern ACSC_EndSequenceM					acsc_EndSequenceM;
extern ACSC_ExtAddPoint						acsc_ExtAddPoint;
extern ACSC_ExtAddPointM					acsc_ExtAddPointM;
extern ACSC_ExtArc1							acsc_ExtArc1;
extern ACSC_ExtArc2							acsc_ExtArc2;
extern ACSC_ExtLine							acsc_ExtLine;
extern ACSC_ExtToPoint						acsc_ExtToPoint;
extern ACSC_ExtToPointM						acsc_ExtToPointM;
extern ACSC_FlushLogFile					acsc_FlushLogFile;
extern ACSC_FlushSCLogFile					acsc_FlushSCLogFile;
extern ACSC_GetAcceleration					acsc_GetAcceleration;
extern ACSC_GetAnalogInput					acsc_GetAnalogInput;
extern ACSC_GetAnalogOutput					acsc_GetAnalogOutput;
extern ACSC_GetAxisState					acsc_GetAxisState;
extern ACSC_GetCommOptions					acsc_GetCommOptions;
extern ACSC_GetDeceleration					acsc_GetDeceleration;
extern ACSC_GetDefaultTimeout				acsc_GetDefaultTimeout;
extern ACSC_GetErrorString					acsc_GetErrorString;
extern ACSC_GetExtInput						acsc_GetExtInput;
extern ACSC_GetExtInputPort					acsc_GetExtInputPort;
extern ACSC_GetExtOutput					acsc_GetExtOutput;
extern ACSC_GetExtOutputPort				acsc_GetExtOutputPort;
extern ACSC_GetFPosition					acsc_GetFPosition;
extern ACSC_GetFVelocity					acsc_GetFVelocity;
extern ACSC_GetFault						acsc_GetFault;
extern ACSC_GetFaultMask					acsc_GetFaultMask;
extern ACSC_GetFirmwareVersion				acsc_GetFirmwareVersion;
extern ACSC_GetHistory						acsc_GetHistory;
extern ACSC_GetIndexState					acsc_GetIndexState;
extern ACSC_GetInput						acsc_GetInput;
extern ACSC_GetInputPort					acsc_GetInputPort;
extern ACSC_GetInterruptMask				acsc_GetInterruptMask;
extern ACSC_GetCallbackMask					acsc_GetCallbackMask;
extern ACSC_GetJerk							acsc_GetJerk;
extern ACSC_GetKillDeceleration				acsc_GetKillDeceleration;
extern ACSC_GetLastError					acsc_GetLastError;
extern ACSC_GetLibraryVersion				acsc_GetLibraryVersion;
extern ACSC_GetMessage						acsc_GetMessage;
extern ACSC_GetMotionError					acsc_GetMotionError;
extern ACSC_GetMotorError					acsc_GetMotorError;
extern ACSC_GetMotorState					acsc_GetMotorState;
extern ACSC_GetOutput						acsc_GetOutput;
extern ACSC_GetOutputPort					acsc_GetOutputPort;
extern ACSC_GetPCICards						acsc_GetPCICards;
extern ACSC_GetEthernetCards				acsc_GetEthernetCards;
extern ACSC_GetProgramError					acsc_GetProgramError;
extern ACSC_GetProgramState					acsc_GetProgramState;
extern ACSC_GetRPosition					acsc_GetRPosition;
extern ACSC_GetRVelocity					acsc_GetRVelocity;
extern ACSC_GetResponseMask					acsc_GetResponseMask;
extern ACSC_GetSafetyInput					acsc_GetSafetyInput;
extern ACSC_GetSafetyInputPort				acsc_GetSafetyInputPort;
extern ACSC_GetSafetyInputPortInv			acsc_GetSafetyInputPortInv;
extern ACSC_GetSerialNumber					acsc_GetSerialNumber;
extern ACSC_GetTimeout						acsc_GetTimeout;
extern ACSC_GetVelocity						acsc_GetVelocity;
extern ACSC_Go								acsc_Go;
extern ACSC_GoM								acsc_GoM;
extern ACSC_Group							acsc_Group;
extern ACSC_Halt							acsc_Halt;
extern ACSC_HaltM							acsc_HaltM;
extern ACSC_Jog								acsc_Jog;
extern ACSC_JogM							acsc_JogM;
extern ACSC_Kill							acsc_Kill;
extern ACSC_KillExt							acsc_KillExt;
extern ACSC_DisableExt						acsc_DisableExt;
extern ACSC_KillAll							acsc_KillAll;
extern ACSC_KillM							acsc_KillM;
extern ACSC_Line							acsc_Line;
extern ACSC_LoadBuffer						acsc_LoadBuffer;
extern ACSC_MultiPoint						acsc_MultiPoint;
extern ACSC_MultiPointM						acsc_MultiPointM;
#if defined(WIN32) && !defined(UNDER_RTSS)
extern ACSC_OpenCommDirect					acsc_OpenCommDirect;
extern ACSC_OpenCommSimulator				acsc_OpenCommSimulator;
extern ACSC_CloseSimulator					acsc_CloseSimulator;
extern ACSC_OpenCommEthernet				acsc_OpenCommEthernet;
extern ACSC_OpenCommEthernetUDP				acsc_OpenCommEthernetUDP;
extern ACSC_OpenCommEthernetTCP				acsc_OpenCommEthernetTCP;
extern ACSC_OpenCommSerial					acsc_OpenCommSerial;
#endif
extern ACSC_OpenCommPCI						acsc_OpenCommPCI;
extern ACSC_OpenHistoryBuffer				acsc_OpenHistoryBuffer;
extern ACSC_OpenLogFile						acsc_OpenLogFile;
extern ACSC_OpenSCLogFile					acsc_OpenSCLogFile;
extern ACSC_OpenMessageBuffer				acsc_OpenMessageBuffer;
extern ACSC_Projection						acsc_Projection;
extern ACSC_ReadDPRAMInteger				acsc_ReadDPRAMInteger;
extern ACSC_ReadDPRAMReal					acsc_ReadDPRAMReal;
extern ACSC_ReadInteger						acsc_ReadInteger;
extern ACSC_ReadReal						acsc_ReadReal;
extern ACSC_Receive							acsc_Receive;
extern ACSC_ReleaseComm						acsc_ReleaseComm;
extern ACSC_ResetIndexState					acsc_ResetIndexState;
extern ACSC_RunBuffer						acsc_RunBuffer;
extern ACSC_Segment							acsc_Segment;
extern ACSC_Send							acsc_Send;
extern ACSC_SetAcceleration					acsc_SetAcceleration;
extern ACSC_SetAccelerationImm				acsc_SetAccelerationImm;
extern ACSC_SetAnalogOutput					acsc_SetAnalogOutput;
extern ACSC_SetCallback						acsc_SetCallback;
extern ACSC_SetCallbackPriority				acsc_SetCallbackPriority;
extern ACSC_SetCommOptions					acsc_SetCommOptions;
extern ACSC_SetDeceleration					acsc_SetDeceleration;
extern ACSC_SetDecelerationImm				acsc_SetDecelerationImm;
extern ACSC_SetExtOutput					acsc_SetExtOutput;
extern ACSC_SetExtOutputPort				acsc_SetExtOutputPort;
extern ACSC_SetFPosition					acsc_SetFPosition;
extern ACSC_SetFaultMask					acsc_SetFaultMask;
extern ACSC_SetInterruptMask				acsc_SetInterruptMask;
extern ACSC_SetCallbackMask					acsc_SetCallbackMask;
extern ACSC_SetIterations					acsc_SetIterations;
extern ACSC_SetJerk							acsc_SetJerk;
extern ACSC_SetJerkImm						acsc_SetJerkImm;
extern ACSC_SetKillDeceleration				acsc_SetKillDeceleration;
extern ACSC_SetKillDecelerationImm			acsc_SetKillDecelerationImm;
extern ACSC_SetMaster						acsc_SetMaster;
extern ACSC_SetOutput						acsc_SetOutput;
extern ACSC_SetOutputPort					acsc_SetOutputPort;
extern ACSC_SetRPosition					acsc_SetRPosition;
extern ACSC_SetResponseMask					acsc_SetResponseMask;
extern ACSC_SetSafetyInputPortInv			acsc_SetSafetyInputPortInv;
extern ACSC_SetTimeout						acsc_SetTimeout;
extern ACSC_SetVelocity						acsc_SetVelocity;
extern ACSC_SetVelocityImm					acsc_SetVelocityImm;
extern ACSC_Slave							acsc_Slave;
extern ACSC_SlaveStalled					acsc_SlaveStalled;
extern ACSC_Spline							acsc_Spline;
extern ACSC_SplineM							acsc_SplineM;
extern ACSC_Split							acsc_Split;
extern ACSC_SplitAll						acsc_SplitAll;
extern ACSC_StopBuffer						acsc_StopBuffer;
extern ACSC_StopCollect						acsc_StopCollect;
extern ACSC_Stopper							acsc_Stopper;
extern ACSC_SuspendBuffer					acsc_SuspendBuffer;
extern ACSC_ToPoint							acsc_ToPoint;
extern ACSC_ToPointM						acsc_ToPointM;
extern ACSC_Transaction						acsc_Transaction;
extern ACSC_UploadBuffer					acsc_UploadBuffer;
extern ACSC_WaitCollectEnd					acsc_WaitCollectEnd;
extern ACSC_WaitCollectEndExt				acsc_WaitCollectEndExt;
extern ACSC_WaitForAsyncCall				acsc_WaitForAsyncCall;
extern ACSC_WaitInput						acsc_WaitInput;
extern ACSC_WaitLogicalMotionEnd			acsc_WaitLogicalMotionEnd;
extern ACSC_WaitMotionEnd					acsc_WaitMotionEnd;
extern ACSC_WaitMotorEnabled				acsc_WaitMotorEnabled;
extern ACSC_WaitMotorCommutated				acsc_WaitMotorCommutated;
extern ACSC_WaitProgramEnd					acsc_WaitProgramEnd;
extern ACSC_WaitUserCondition				acsc_WaitUserCondition;
extern ACSC_WriteDPRAMInteger				acsc_WriteDPRAMInteger;
extern ACSC_WriteDPRAMReal					acsc_WriteDPRAMReal;
extern ACSC_WriteInteger					acsc_WriteInteger;
extern ACSC_WriteLogFile					acsc_WriteLogFile;
extern ACSC_WriteSCLogFile					acsc_WriteSCLogFile;
extern ACSC_WriteReal						acsc_WriteReal;
extern ACSC_LoadBufferIgnoreServiceLines	acsc_LoadBufferIgnoreServiceLines;
extern ACSC_LoadBuffersFromFile				acsc_LoadBuffersFromFile;

extern ACSC_PegI							acsc_PegI;
extern ACSC_PegR							acsc_PegR;
extern ACSC_PegInc							acsc_PegInc;
extern ACSC_PegRandom						acsc_PegRandom;
extern ACSC_AssignPins						acsc_AssignPins;
extern ACSC_StopPeg							acsc_StopPeg;

extern ACSC_AssignPegNT						acsc_AssignPegNT;
extern ACSC_AssignPegOutputsNT				acsc_AssignPegOutputsNT;
extern ACSC_AssignFastInputsNT				acsc_AssignFastInputsNT;
extern ACSC_PegIncNT						acsc_PegIncNT;
extern ACSC_PegRandomNT						acsc_PegRandomNT;
extern ACSC_WaitPegReadyNT					acsc_WaitPegReadyNT;
extern ACSC_StartPegNT						acsc_StartPegNT;
extern ACSC_StopPegNT						acsc_StopPegNT;

extern ACSC_CollectB						acsc_CollectB;
extern ACSC_DataCollection					acsc_DataCollection;
extern ACSC_DataCollectionExt				acsc_DataCollectionExt;
extern ACSC_AddPVPoint						acsc_AddPVPoint;
extern ACSC_AddPVPointM						acsc_AddPVPointM;
extern ACSC_AddPVTPoint						acsc_AddPVTPoint;
extern ACSC_AddPVTPointM					acsc_AddPVTPointM;
extern ACSC_LoadFileToRealVariable			acsc_LoadFileToRealVariable;
extern ACSC_LoadFileToIntegerVariable		acsc_LoadFileToIntegerVariable;
extern ACSC_LoadDataToController			acsc_LoadDataToController;
extern ACSC_UploadDataFromController		acsc_UploadDataFromController;
extern ACSC_SetQueueOverflowTimeout			acsc_SetQueueOverflowTimeout;
extern ACSC_GetQueueOverflowTimeout			acsc_GetQueueOverflowTimeout;
extern ACSC_SetTargetPosition				acsc_SetTargetPosition;
extern ACSC_GetTargetPosition				acsc_GetTargetPosition;
extern ACSC_SetTargetPositionM				acsc_SetTargetPositionM;
extern ACSC_Track							acsc_Track;
extern ACSC_TrackM							acsc_TrackM;
extern ACSC_FaultClearM						acsc_FaultClearM;
extern ACSC_FaultClear						acsc_FaultClear;
extern ACSC_Getconf							acsc_Getconf;
extern ACSC_Setconf							acsc_Setconf;
extern ACSC_GetConf							acsc_GetConf;
extern ACSC_SetConf							acsc_SetConf;
extern ACSC_SysInfo							acsc_SysInfo;

extern ACSC_GetAxesCount					acsc_GetAxesCount;
extern ACSC_GetBuffersCount					acsc_GetBuffersCount;
extern ACSC_GetDBufferIndex					acsc_GetDBufferIndex;

extern ACSC_SetCallbackExt					acsc_SetCallbackExt;
extern ACSC_InstallCallback					acsc_InstallCallback;
extern ACSC_DownloadBinVariableToFile		acsc_DownloadBinVariableToFile;
extern ACSC_SetLogFileOptions				acsc_SetLogFileOptions;

extern ACSC_SetServer						acsc_SetServer;
extern ACSC_SetServerExt					acsc_SetServerExt;
extern ACSC_SetServerExtLogin				acsc_SetServerExtLogin;

extern ACSC_GetSingleMessage				acsc_GetSingleMessage;

extern ACSC_GetConnectionsList			    acsc_GetConnectionsList;
extern ACSC_GetConnectionInfo			    acsc_GetConnectionInfo;
extern ACSC_TerminateConnection				acsc_TerminateConnection;

extern ACSC_GetLogData						acsc_GetLogData;

extern ACSC_RegisterEmergencyStop			acsc_RegisterEmergencyStop;
extern ACSC_UnregisterEmergencyStop			acsc_UnregisterEmergencyStop;

extern ACSC_GetUMDVersion					acsc_GetUMDVersion;

extern ACSC_AnalyzeApplication				acsc_AnalyzeApplication; 
extern ACSC_FreeApplication		        	acsc_FreeApplication;	
extern ACSC_SaveApplication					acsc_SaveApplication;    
extern ACSC_LoadApplication					acsc_LoadApplication;	

extern ACSC_ControllerReboot				acsc_ControllerReboot;
extern ACSC_ControllerFactoryDefault		acsc_ControllerFactoryDefault;
extern ACSC_ControllerSaveToFlash			acsc_ControllerSaveToFlash;

extern ACSC_GetSharedMemoryAddress			acsc_GetSharedMemoryAddress;
extern ACSC_ReadSharedMemoryReal			acsc_ReadSharedMemoryReal;
extern ACSC_ReadSharedMemoryInteger			acsc_ReadSharedMemoryInteger;
extern ACSC_WriteSharedMemoryReal			acsc_WriteSharedMemoryReal;
extern ACSC_WriteSharedMemoryInteger		acsc_WriteSharedMemoryInteger;

extern ACSC_GetEtherCATState				acsc_GetEtherCATState;
extern ACSC_GetEtherCATError				acsc_GetEtherCATError;
extern ACSC_MapEtherCATInput				acsc_MapEtherCATInput;
extern ACSC_MapEtherCATOutput				acsc_MapEtherCATOutput;
extern ACSC_UnmapEtherCATInputsOutputs		acsc_UnmapEtherCATInputsOutputs;
extern ACSC_GetEtherCATSlaveIndex			acsc_GetEtherCATSlaveIndex;
extern ACSC_GetEtherCATSlaveOffset			acsc_GetEtherCATSlaveOffset;
extern ACSC_GetEtherCATSlaveVendorID		acsc_GetEtherCATSlaveVendorID;
extern ACSC_GetEtherCATSlaveProductID		acsc_GetEtherCATSlaveProductID;
extern ACSC_GetEtherCATSlaveRevision		acsc_GetEtherCATSlaveRevision;
extern ACSC_GetEtherCATSlaveType			acsc_GetEtherCATSlaveType;
extern ACSC_GetEtherCATSlaveState			acsc_GetEtherCATSlaveState;
extern ACSC_DownloadFileOverEtherCAT		acsc_DownloadFileOverEtherCAT;
extern ACSC_ReadSDOValueOverEtherCAT		acsc_ReadSDOValueOverEtherCAT;
extern ACSC_WriteSDOValueOverEtherCAT		acsc_WriteSDOValueOverEtherCAT;

extern ACSC_CopyFileToController			acsc_CopyFileToController;
extern ACSC_DeleteFileFromController		acsc_DeleteFileFromController;

extern ACSC_SegmentedMotion					acsc_SegmentedMotion;
extern ACSC_ExtendedSegmentedMotion			acsc_ExtendedSegmentedMotion;
extern ACSC_ExtendedSegmentedMotionExt		acsc_ExtendedSegmentedMotionExt;
extern ACSC_SegmentLine						acsc_SegmentLine;
extern ACSC_SegmentLineExt					acsc_SegmentLineExt;
extern ACSC_SegmentArc1						acsc_SegmentArc1;
extern ACSC_SegmentArc2						acsc_SegmentArc2;
extern ACSC_SegmentArc1Ext					acsc_SegmentArc1Ext;
extern ACSC_SegmentArc2Ext					acsc_SegmentArc2Ext;

extern ACSC_BlendedSegmentMotion			acsc_BlendedSegmentMotion;
extern ACSC_BlendedLine						acsc_BlendedLine;
extern ACSC_BlendedArc1						acsc_BlendedArc1;
extern ACSC_BlendedArc2						acsc_BlendedArc2;

extern ACSC_GetAnalogInputNT				acsc_GetAnalogInputNT;
extern ACSC_GetAnalogOutputNT				acsc_GetAnalogOutputNT;
extern ACSC_SetAnalogOutputNT				acsc_SetAnalogOutputNT;

extern ACSC_GetVolatileMemoryUsage			acsc_GetVolatileMemoryUsage;
extern ACSC_GetVolatileMemoryTotal			acsc_GetVolatileMemoryTotal;
extern ACSC_GetVolatileMemoryFree			acsc_GetVolatileMemoryFree;
extern ACSC_GetNonVolatileMemoryUsage		acsc_GetNonVolatileMemoryUsage;
extern ACSC_GetNonVolatileMemoryTotal		acsc_GetNonVolatileMemoryTotal;
extern ACSC_GetNonVolatileMemoryFree		acsc_GetNonVolatileMemoryFree;

extern ACSC_StartSPiiPlusSC					acsc_StartSPiiPlusSC;
extern ACSC_StopSPiiPlusSC					acsc_StopSPiiPlusSC;
extern HMODULE hACSCLibraryModule;

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function loads ACSC.DLL and obtains addresses for all exported functions.
// Call this function before any using of ACSC API.
// Check return value for success.
//////////////////////////////////////////////////////////////////////////////////////////////////
extern int InitACSCLibrary();

//////////////////////////////////////////////////////////////////////////////////////////////////
// The function unmapps from the address space of the calling process.
//////////////////////////////////////////////////////////////////////////////////////////////////
extern int FreeACSCLibrary();

#endif

#endif

#ifdef __cplusplus
}
#endif



//////////////////////////////////////////////////////////////////////////////////////////////////
// Internal functions that save and read a global errors
//////////////////////////////////////////////////////////////////////////////////////////////////
// Save last global error
void SetGlobalError(DWORD dwError);
// Read last global error
DWORD GetGlobalError();

#endif
